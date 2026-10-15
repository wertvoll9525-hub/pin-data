"""수집기 공통: 키 읽기, 재시도·간격이 있는 호출, 페이지 순회, 좌표 검사, 격자."""
import json, math, os, sys, time, urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
API = 'https://apis.data.go.kr/'
GAP = 0.15          # 요청 사이 간격(초)
LAT = (33.0, 39.0)
LON = (124.0, 132.0)


def _env():
    e = {}
    p = os.path.join(HERE, '.env')
    if os.path.exists(p):
        for l in open(p, encoding='utf-8'):
            if '=' in l:
                k, v = l.strip().split('=', 1)
                e[k] = v.strip().strip('"')
    for k in ('DATA_GO_KR_KEY', 'KAKAO_REST_KEY'):
        if os.environ.get(k):
            e[k] = os.environ[k]
    return e


ENV = _env()


class UpstreamError(Exception):
    pass


def call(path, params=None, tries=4):
    """공공 API 한 번 호출. 본문 bytes를 돌려준다. HTTP 200 안의 오류도 예외로 올린다."""
    q = dict(serviceKey=ENV['DATA_GO_KR_KEY'], **(params or {}))
    url = API + path + '?' + urllib.parse.urlencode(q)
    last = None
    for i in range(tries):
        try:
            time.sleep(GAP)
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'pin-pipeline'}), timeout=120) as r:
                body = r.read()
            head = body[:400].decode('utf-8', 'replace')
            if 'SERVICE_KEY' in head or 'LIMITED_NUMBER' in head or 'OpenAPI_ServiceResponse' in head:
                raise UpstreamError(head.replace('\n', ' ')[:200])
            return body
        except (urllib.error.URLError, TimeoutError, UpstreamError) as e:
            last = e
            time.sleep(2 * (i + 1))
    raise UpstreamError(f'{path}: {last}')


def xml_items(body):
    root = ET.fromstring(body)
    total = int(root.findtext('.//totalCount') or 0)
    items = [{c.tag: (c.text or '').strip() for c in it} for it in root.iter('item')]
    return total, items


def pages_xml(path, params, rows=1000, limit=None):
    """XML API를 totalCount까지 순회."""
    out, page, total = [], 1, None
    while True:
        t, items = xml_items(call(path, dict(params, pageNo=page, numOfRows=rows)))
        total = t if total is None else total
        out += items
        if not items or len(out) >= total or (limit and page >= limit):
            return out
        page += 1


def in_korea(la, lo):
    return la is not None and lo is not None and LAT[0] <= la <= LAT[1] and LON[0] <= lo <= LON[1]


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def r5(v):
    return round(v, 5)


def cell(la, lo):
    return f'{math.floor(la * 10)}_{math.floor(lo * 10)}'


def place(id_, cat, name, la, lo, addr, tel=None, hours=None, note=None, **extra):
    d = {'id': id_, 'c': cat, 'n': name, 'la': r5(la), 'lo': r5(lo), 'a': addr}
    if tel:
        d['t'] = tel
    if hours:
        d['h'] = hours
    if note:
        d['x'] = note
    d.update(extra)
    return d


def log(*a):
    print(*a, file=sys.stderr, flush=True)
