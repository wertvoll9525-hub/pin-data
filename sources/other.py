"""그 밖의 수집기: 동물병원, 전기차, 수소, 공영주차장, 민방위 대피소, 공휴일."""
import json, time, urllib.parse, urllib.request
from pyproj import Transformer
from common import ENV, call, pages_xml, num, in_korea, place, log

VET_EPSG = 'EPSG:5174'   # 지방행정 인허가 TM(중부원점). check.py의 대조 결과로 확정
_tm = Transformer.from_crs(VET_EPSG, 'EPSG:4326', always_xy=True)
_tm5179 = Transformer.from_crs('EPSG:5179', 'EPSG:4326', always_xy=True)


def _json_pages(path, params, rows, items_of, total_of, limit=None):
    out, page = [], 1
    while True:
        d = json.loads(call(path, dict(params, pageNo=page, numOfRows=rows)))
        items = items_of(d) or []
        if isinstance(items, dict):
            items = [items]
        out += items
        total = int(total_of(d) or 0)
        if not items or len(out) >= total or (limit and page >= limit):
            return out
        page += 1


def vet():
    rows = _json_pages('1741000/animal_hospitals/info', {'returnType': 'JSON'}, 100,
                       lambda d: d['response']['body']['items']['item'],
                       lambda d: d['response']['body']['totalCount'])
    out, bad = [], 0
    for it in rows:
        if it.get('SALS_STTS_CD') != '01':       # 영업/정상만
            continue
        x, y = num(it.get('CRD_INFO_X')), num(it.get('CRD_INFO_Y'))
        if x is None or y is None:
            bad += 1
            continue
        lo, la = _tm.transform(x, y)
        if not in_korea(la, lo):
            bad += 1
            continue
        addr = it.get('ROAD_NM_ADDR') or it.get('LOTNO_ADDR') or ''
        out.append(place(it['MNG_NO'], 'VET', it['BPLC_NM'], la, lo, addr, it.get('TELNO')))
    return out, bad


def _ev_kind(it):
    kw = num(it.get('output'))
    if kw:
        return 'F' if kw >= 50 else 'S'
    return 'S' if it.get('chgerType') == '02' else 'F'


def ev():
    """충전기 행을 충전소 단위로 묶는다. 급속/완속 기수는 x에 문자열로."""
    zcodes = ['11', '26', '27', '28', '29', '30', '31', '36', '41', '43', '44', '46', '47', '48', '50', '51', '52']
    st = {}
    for z in zcodes:
        for it in pages_xml('B552584/EvCharger/getChargerInfo', {'zcode': z}, rows=9999):
            if it.get('delYn') == 'Y':
                continue
            s = st.setdefault(it['statId'], {'it': it, 'F': 0, 'S': 0, 'ids': []})
            s[_ev_kind(it)] += 1
            s['ids'].append(it['chgerId'])
    out, bad = [], 0
    for sid, s in st.items():
        it = s['it']
        la, lo = num(it.get('lat')), num(it.get('lng'))
        if not in_korea(la, lo):
            bad += 1
            continue
        parts = ([f"급속 {s['F']}기"] if s['F'] else []) + ([f"완속 {s['S']}기"] if s['S'] else [])
        note = ' · '.join(parts + ([it['useTime']] if it.get('useTime') else []))
        out.append(place(sid, 'EV', it['statNm'], la, lo, (it.get('addr', '') + ' ' + it.get('addrDetail', '')).strip(),
                         it.get('busiCall'), None, note, f=s['F'], s=s['S'], op=it.get('busiNm')))
    return out, bad


def h2():
    """실시간 API엔 좌표가 없다. 카카오 키워드 검색으로 이름→좌표(키 필요)."""
    d = json.loads(call('B552532/h2nbiz_3/currentInfo', {}))
    items = d['body']['items']['item']
    key = ENV.get('KAKAO_REST_KEY')
    if not key:
        log('H2: KAKAO_REST_KEY 없음 → 좌표를 만들 수 없어 건너뜀 (USER_TODO 3)')
        return None, len(items)
    out, bad = [], 0
    for it in items:
        name = it['chrstn_nm']
        q = urllib.parse.quote(name.split('(')[0].strip())
        req = urllib.request.Request('https://dapi.kakao.com/v2/local/search/keyword.json?query=' + q,
                                     headers={'Authorization': 'KakaoAK ' + key})
        time.sleep(0.1)
        docs = json.load(urllib.request.urlopen(req, timeout=30)).get('documents', [])
        if not docs:
            bad += 1
            continue
        g = docs[0]
        out.append(place(it['chrstn_mno'], 'H2', name, float(g['y']), float(g['x']),
                         g.get('road_address_name') or g.get('address_name', ''), g.get('phone') or None))
    return out, bad


def parking():
    """공영만. 목록은 공영이 앞쪽에 모여 있어서 공영이 없는 페이지가 나오면 멈춘다."""
    out, bad, seen, page = [], 0, set(), 1
    while True:
        d = json.loads(call('B553881/Parking_v1/PrkSttusInfo_v1', {'format': '2', 'pageNo': page, 'numOfRows': 1000}))
        rows = d.get('PrkSttusInfo') or []
        pub = [r for r in rows if r.get('prk_manage_agent_nm') == '공영']
        for it in pub:
            pid = it['prk_center_id']
            if pid in seen:
                continue
            seen.add(pid)
            la, lo = num(it.get('prk_plce_entrc_la')), num(it.get('prk_plce_entrc_lo'))
            if not in_korea(la, lo):
                bad += 1
                continue
            cap = it.get('prk_cmprt_co')
            note = ' · '.join(x for x in (it.get('parkng_chrge_se_nm'), f'{cap}면' if cap else '') if x)
            out.append(place(pid, 'PARKING', it['prk_plce_nm'], la, lo,
                             it.get('prk_plce_adres') or f"{it.get('prk_plce_adres_sido','')} {it.get('prk_plce_adres_sigungu','')}".strip(),
                             None, None, note or None))
        if not pub:
            return out, bad
        page += 1


def civil():
    rows = _json_pages('1741000/civil_defense_shelter_info/info', {'returnType': 'JSON'}, 100,
                       lambda d: d['response']['body']['items']['item'],
                       lambda d: d['response']['body']['totalCount'])
    out, bad = [], 0
    for it in rows:
        if it.get('OPER_STTS') not in (None, '', '사용중'):
            continue
        la, lo = num(it.get('LAT_EPSG4326')), num(it.get('LOT_EPST4326'))
        if not in_korea(la, lo):
            x, y = num(it.get('CRD_INFO_X_EPSG5179')), num(it.get('CRD_INFO_Y_EPSG5179'))
            if x is not None and y is not None:
                lo, la = _tm5179.transform(x, y)
        if not in_korea(la, lo):
            bad += 1
            continue
        loc = ' '.join(x for x in (it.get('FCLTLOC_GRND_UDGD'), '') if x)
        cap = it.get('MAX_ACTC_PERNE')
        note = ' · '.join(x for x in (loc, f'{int(float(cap))}명' if cap else '') if x)
        out.append(place(it['MNG_NO'], 'CIVIL_SHELTER', it['FCLT_NM'], la, lo,
                         it.get('ROAD_NM_WHOL_ADDR') or it.get('LCTN_WHOL_ADDR') or '', None, None, note or None))
    return out, bad


def holidays(years):
    from common import xml_items
    days = []
    for y in years:
        _, items = xml_items(call('B090041/openapi/service/SpcdeInfoService/getRestDeInfo',
                                  {'solYear': y, 'numOfRows': 100}))
        days += [i['locdate'] for i in items if i.get('isHoliday') == 'Y']
    return sorted(set(f'{d[:4]}-{d[4:6]}-{d[6:]}' for d in days))
