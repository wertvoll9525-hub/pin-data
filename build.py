"""전량 수집 → 정리 → 격자 파일 → meta.json. 결과는 out/v1/ 아래.

실패한 장소는 이전 out 파일을 그대로 두고 summary.json에 기록한다(Actions는 실패로 표시하지 않음).
사용: python build.py [CATEGORY ...]
"""
import datetime as dt, gzip, json, os, shutil, sys, time, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import HERE, cell, log
from sources import nmc, other

OUT = os.path.join(HERE, 'out', 'v1')
ALL_THRESHOLD = 5000
KST = dt.timezone(dt.timedelta(hours=9))

# 코드: (수집 함수, 출처 표기)
SOURCES = {
    'PHARMACY':     (nmc.pharmacy, '국립중앙의료원'),
    'NIGHT_CLINIC': (nmc.night_clinic, '국립중앙의료원'),
    'ER':           (nmc.er, '국립중앙의료원'),
    'AED':          (nmc.aed, '국립중앙의료원'),
    'VET':          (other.vet, '행정안전부'),
    'EV':           (other.ev, '한국환경공단'),
    'H2':           (other.h2, '한국석유관리원'),
    'PARKING':      (other.parking, '한국교통안전공단'),
    'CIVIL_SHELTER': (other.civil, '행정안전부'),
}


def write_gz(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path, 'wt', encoding='utf-8', compresslevel=9) as f:
        json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))


def publish(cat, places):
    d = os.path.join(OUT, cat)
    shutil.rmtree(d, ignore_errors=True)
    if len(places) < ALL_THRESHOLD:
        write_gz(os.path.join(d, 'all.json.gz'), places)
        return 'all'
    grid = {}
    for p in places:
        grid.setdefault(cell(p['la'], p['lo']), []).append(p)
    for k, v in grid.items():
        write_gz(os.path.join(d, f'{k}.json.gz'), v)
    return 'grid'


def main(only):
    os.makedirs(OUT, exist_ok=True)
    mp = os.path.join(OUT, 'meta.json')
    meta = json.load(open(mp, encoding='utf-8')) if os.path.exists(mp) else {'cats': {}}
    sp = os.path.join(HERE, 'out', 'summary.json')
    summary = json.load(open(sp, encoding='utf-8')) if only and os.path.exists(sp) else {}
    today = dt.datetime.now(KST).date().isoformat()
    for cat, (fn, src) in SOURCES.items():
        if only and cat not in only:
            continue
        t = time.time()
        try:
            places, bad = fn()
            if places is None:
                summary[cat] = {'status': 'skipped', 'reason': 'no coordinates source', 'dropped': bad}
                continue
            uniq = {}
            for p in places:
                uniq.setdefault(p['id'], p)
            places = list(uniq.values())
            if not places:
                raise RuntimeError('0 places')
            mode = publish(cat, places)
            meta['cats'][cat] = {'mode': mode, 'count': len(places), 'source': src, 'asOf': today}
            summary[cat] = {'status': 'ok', 'count': len(places), 'dropped_bad_coords': bad, 'mode': mode,
                            'sec': round(time.time() - t)}
        except Exception as e:
            log(f'[{cat}] failed: {e}')
            traceback.print_exc()
            summary[cat] = {'status': 'failed', 'error': str(e)[:300], 'kept_previous': cat in meta['cats']}
        log(cat, summary[cat])
    if not only:
        from sources.other import holidays
        y = dt.datetime.now(KST).year
        try:
            json.dump({'years': [y, y + 1], 'dates': holidays([y, y + 1])},
                      open(os.path.join(OUT, 'holidays.json'), 'w', encoding='utf-8'), ensure_ascii=False)
            summary['HOLIDAYS'] = {'status': 'ok'}
        except Exception as e:
            summary['HOLIDAYS'] = {'status': 'failed', 'error': str(e)[:300]}
    meta['generated'] = dt.datetime.now(KST).isoformat(timespec='seconds')
    # 삭제된 장소 폴더가 meta에 남지 않게: SOURCES에 없는 코드는 제거
    meta['cats'] = {k: v for k, v in meta['cats'].items() if k in SOURCES}
    json.dump(meta, open(mp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(summary, open(sp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main(set(sys.argv[1:]))
