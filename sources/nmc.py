"""국립중앙의료원 4종: 약국, 야간·휴일 병원, 응급실, 자동심장충격기."""
from common import pages_xml, num, in_korea, place, log

B = 'B552657/'
DAYS = {1: 'mon', 2: 'tue', 3: 'wed', 4: 'thu', 5: 'fri', 6: 'sat', 7: 'sun', 8: 'hol'}


def _duty_hours(it):
    """dutyTime{1..8}s/c → {"1":["0900","1800"]}. 8=공휴일. 빈 요일은 키 없음."""
    h = {}
    for d in range(1, 9):
        s, c = it.get(f'dutyTime{d}s', ''), it.get(f'dutyTime{d}c', '')
        if s and c:
            h[str(d)] = [s.zfill(4), c.zfill(4)]
    return h


# 진료과목 코드(QD) → 이름. 병원 60곳·400곳의 실제 진료과목 이름과 코드별 목록을 대조해 맞춘 것(일치율 100%).
# 표본에 거의 안 나온 코드(D007 등)와 치과·한방 코드는 이름을 확인하지 못해 넣지 않았다.
DEPT_CODES = {
    'D001': '내과', 'D002': '소아청소년과', 'D003': '신경과', 'D004': '정신건강의학과', 'D005': '피부과',
    'D006': '외과', 'D008': '정형외과', 'D009': '신경외과', 'D010': '성형외과', 'D011': '산부인과',
    'D012': '안과', 'D013': '이비인후과', 'D014': '비뇨의학과', 'D016': '재활의학과', 'D017': '마취통증의학과',
    'D018': '영상의학과', 'D022': '가정의학과', 'D024': '응급의학과', 'D033': '진단검사의학과',
}
DEPT_ALIASES = {'소아과': '소아청소년과', '소아 청소년과': '소아청소년과', '이비인후': '이비인후과', '정신과': '정신건강의학과'}


def normalize_dept(name):
    """공백·표기 차이를 정리한다. 알려진 별칭은 대표 이름으로."""
    n = ''.join((name or '').split())
    for k, v in DEPT_ALIASES.items():
        if n == ''.join(k.split()):
            return v
    return n


def _dept_map():
    """{hpid: [진료과목...]}. 과목 코드별로 병원 목록을 받아 뒤집는다(병원마다 기본정보를 따로 받으면 2만 건이 넘는다)."""
    m = {}
    for code, name in DEPT_CODES.items():
        for it in pages_xml(B + 'HsptlAsembySearchService/getHsptlMdcncListInfoInqire', {'QD': code}, rows=1000):
            if it.get('hpid'):
                m.setdefault(it['hpid'], []).append(normalize_dept(name))
        log(f'  진료과목 {code} {name}: 누적 {len(m)}곳')
    return m


def pharmacy():
    out, bad = [], 0
    for it in pages_xml(B + 'ErmctInsttInfoInqireService/getParmacyFullDown', {}):
        la, lo = num(it.get('wgs84Lat')), num(it.get('wgs84Lon'))
        if not in_korea(la, lo):
            bad += 1
            continue
        out.append(place(it['hpid'], 'PHARMACY', it['dutyName'], la, lo, it.get('dutyAddr', ''),
                         it.get('dutyTel1'), _duty_hours(it)))
    return out, bad


def night_clinic():
    out, bad = [], 0
    try:
        depts = _dept_map()
    except Exception as e:   # 진료과목만 못 받아도 병원 목록은 낸다
        log(f'[NIGHT_CLINIC] 진료과목 수집 실패, 과목 없이 진행: {e}')
        depts = {}
    for it in pages_xml(B + 'HsptlAsembySearchService/getHsptlMdcncFullDown', {}):
        if it.get('dutyDivNam') == '요양병원':   # 요양병원은 24시간이라 걸리지만 급할 때 찾는 곳이 아니다
            continue
        h = _duty_hours(it)
        night = any(h.get(str(d), ['0', '0'])[1] >= '2000' for d in range(1, 6))
        off = '7' in h or '8' in h       # 토요일은 거의 전부 있어 기준에서 뺀다
        if not (night or off):
            continue
        la, lo = num(it.get('wgs84Lat')), num(it.get('wgs84Lon'))
        if not in_korea(la, lo):
            bad += 1
            continue
        extra = {'d': depts[it['hpid']]} if depts.get(it['hpid']) else {}
        out.append(place(it['hpid'], 'NIGHT_CLINIC', it['dutyName'], la, lo, it.get('dutyAddr', ''),
                         it.get('dutyTel1'), h, it.get('dutyDivNam') or None, **extra))
    return out, bad


def er():
    out, bad = [], 0
    for it in pages_xml(B + 'ErmctInfoInqireService/getEgytListInfoInqire', {}):
        la, lo = num(it.get('wgs84Lat')), num(it.get('wgs84Lon'))
        if not in_korea(la, lo):
            bad += 1
            continue
        out.append(place(it['hpid'], 'ER', it['dutyName'], la, lo, it.get('dutyAddr', ''),
                         it.get('dutyTel3') or it.get('dutyTel1'), None, it.get('dutyEmclsName') or None))
    return out, bad


def aed():
    out, bad = [], 0
    for it in pages_xml(B + 'AEDInfoInqireService/getEgytAedManageInfoInqire', {}):
        la, lo = num(it.get('wgs84Lat')), num(it.get('wgs84Lon'))
        if not in_korea(la, lo):
            bad += 1
            continue
        h = {}
        for d, k in DAYS.items():
            s, e = it.get(f'{k}SttTme', ''), it.get(f'{k}EndTme', '')
            if s and e:
                h[str(d)] = [s.zfill(4), e.zfill(4)]
        place_ = it.get('buildPlace', '')
        out.append(place(it.get('serialSeq') or f"{la:.5f},{lo:.5f}", 'AED', it.get('org') or place_, la, lo,
                         it.get('buildAddress', ''), it.get('clerkTel'), h, place_ or None))
    return out, bad
