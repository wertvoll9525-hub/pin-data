"""장소별 실제 응답을 1페이지씩 받아 samples/ 에 저장한다 (키는 저장하지 않음)."""
import os, sys, urllib.request, urllib.parse, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
env = dict(l.strip().split('=', 1) for l in open(os.path.join(HERE, '.env'), encoding='utf-8') if '=' in l)
KEY = env['DATA_GO_KR_KEY'].strip().strip('"')
B = 'https://apis.data.go.kr/'

# 이름: (경로, 확장 파라미터, 확장자)
SRC = {
    'pharmacy':      ('B552657/ErmctInsttInfoInqireService/getParmacyFullDown', {}, 'xml'),
    'night_clinic':  ('B552657/HsptlAsembySearchService/getHsptlMdcncFullDown', {}, 'xml'),
    'er_list':       ('B552657/ErmctInfoInqireService/getEgytListInfoInqire', {'Q0': '충청북도'}, 'xml'),
    'er_realtime':   ('B552657/ErmctInfoInqireService/getEmrrmRltmUsefulSckbdInfoInqire', {'STAGE1': '충청북도'}, 'xml'),
    'aed':           ('B552657/AEDInfoInqireService/getEgytAedManageInfoInqire', {'Q0': '충청북도', 'Q1': '증평군'}, 'xml'),
    'vet':           ('1741000/animal_hospitals/info', {'returnType': 'JSON'}, 'json'),
    'ev_info':       ('B552584/EvCharger/getChargerInfo', {'zcode': '43'}, 'xml'),
    'ev_status':     ('B552584/EvCharger/getChargerStatus', {'zcode': '43'}, 'xml'),
    'h2_realtime':   ('B552532/h2nbiz_3/currentInfo', {}, 'json'),
    'parking_info':  ('B553881/Parking_v1/PrkSttusInfo_v1', {'format': '2'}, 'json'),
    'parking_rt':    ('B553881/Parking_v1/PrkRealtimeInfo_v1', {'format': '2'}, 'json'),
    'civil_shelter': ('1741000/civil_defense_shelter_info/info', {'returnType': 'JSON'}, 'json'),
    'holiday':       ('B090041/openapi/service/SpcdeInfoService/getRestDeInfo', {'solYear': '2026'}, 'xml'),
}

def fetch(name, rows=5):
    path, extra, ext = SRC[name]
    q = dict(serviceKey=KEY, pageNo=1, numOfRows=rows, **extra)
    url = B + path + '?' + urllib.parse.urlencode(q)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'pin'}), timeout=60) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()

if __name__ == '__main__':
    os.makedirs(os.path.join(HERE, 'samples'), exist_ok=True)
    for n in (sys.argv[1:] or SRC):
        st, body = fetch(n)
        out = os.path.join(HERE, 'samples', f'{n}.{SRC[n][2]}')
        open(out, 'wb').write(body)
        assert KEY.encode() not in body
        print(n, st, len(body))
