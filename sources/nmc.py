"""국립중앙의료원 4종: 약국, 야간·휴일 병원, 응급실, 자동심장충격기."""
from common import pages_xml, num, in_korea, place

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
        out.append(place(it['hpid'], 'NIGHT_CLINIC', it['dutyName'], la, lo, it.get('dutyAddr', ''),
                         it.get('dutyTel1'), h, it.get('dutyDivNam') or None))
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
