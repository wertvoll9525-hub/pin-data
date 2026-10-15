"""out/ 검증: 개수 상식 범위, 무작위 5곳 주소·좌표 대조(카카오), 운영시간 파싱 실패율.

사용: python check.py            (KAKAO_REST_KEY 없으면 주소 대조는 건너뜀)
"""
import glob, gzip, json, math, os, random, re, sys, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ENV, HERE

OUT = os.path.join(HERE, 'out', 'v1')
# (최소, 최대) — 상식 범위. 벗어나면 실패
RANGE = {'PHARMACY': (15000, 40000), 'NIGHT_CLINIC': (5000, 60000), 'ER': (300, 800), 'AED': (30000, 120000),
         'VET': (3000, 12000), 'EV': (40000, 400000), 'H2': (100, 600), 'PARKING': (5000, 60000),
         'CIVIL_SHELTER': (8000, 40000)}
HHMM = re.compile(r'^(?:[01]\d|2[0-5])[0-5]\d$')


def load(cat):
    out = []
    for f in glob.glob(os.path.join(OUT, cat, '*.json.gz')):
        out += json.load(gzip.open(f, 'rt', encoding='utf-8'))
    return out


def kakao_region(la, lo):
    req = urllib.request.Request(
        f'https://dapi.kakao.com/v2/local/geo/coord2regioncode.json?x={lo}&y={la}',
        headers={'Authorization': 'KakaoAK ' + ENV['KAKAO_REST_KEY']})
    docs = json.load(urllib.request.urlopen(req, timeout=20)).get('documents', [])
    return (docs[0]['region_1depth_name'], docs[0]['region_2depth_name']) if docs else None


def main():
    meta = json.load(open(os.path.join(OUT, 'meta.json'), encoding='utf-8'))
    fails = []
    print('== 개수')
    for cat, (lo, hi) in RANGE.items():
        c = meta['cats'].get(cat, {}).get('count', 0)
        flag = 'OK ' if lo <= c <= hi else 'FAIL'
        if flag == 'FAIL':
            fails.append(cat)
        print(f'  {flag} {cat:14s} {c:>8,}  (기대 {lo:,}~{hi:,})')
    print('== 운영시간 파싱 실패율 (형식 HHMM, 시작<끝 또는 24시간/자정 넘김 허용)')
    for cat in meta['cats']:
        ps = load(cat)
        with_h = [p for p in ps if p.get('h')]
        bad = sum(1 for p in with_h if any(not (HHMM.match(a) and HHMM.match(b)) for a, b in p['h'].values() if a and b))
        print(f'  {cat:14s} 운영시간 있음 {len(with_h):>7,}/{len(ps):>7,}  형식오류 {bad:>5,} ({(bad / len(with_h) * 100 if with_h else 0):.2f}%)')
    print('== 무작위 5곳 좌표↔주소 (카카오 coord2regioncode)')
    if not ENV.get('KAKAO_REST_KEY'):
        print('  건너뜀: KAKAO_REST_KEY 없음 (USER_TODO 3)')
        return 1 if fails else 0
    random.seed(7)
    for cat in meta['cats']:
        ps = load(cat)
        ok = 0
        for p in random.sample(ps, min(5, len(ps))):
            r = kakao_region(p['la'], p['lo'])
            # 시·도 이름은 약칭(충북)·행정구역 통합(전남광주) 때문에 비교하지 않고 시·군·구로 맞춘다
            match = bool(r) and r[1].split()[0] in p['a']
            ok += match
            if not match:
                print(f'    불일치 {cat} {p["n"]} | 주소={p["a"]} | 좌표→{r}')
        print(f'  {cat:14s} {ok}/5 일치')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
