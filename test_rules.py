"""수집기 규칙 확인(네트워크 없이). 실행: python test_rules.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DATA_GO_KR_KEY', 'test')

from sources import nmc, other  # noqa: E402


def test_dept_normalize():
    assert nmc.normalize_dept('소아과') == '소아청소년과'
    assert nmc.normalize_dept(' 소아 청소년과 ') == '소아청소년과'
    assert nmc.normalize_dept('내 과') == '내과'
    assert nmc.normalize_dept('이비인후과') == '이비인후과'
    assert nmc.normalize_dept(None) == ''


def test_dept_codes_are_unique_names():
    names = list(nmc.DEPT_CODES.values())
    assert len(names) == len(set(names))
    # 앱 칩 5개는 모두 코드표에 있어야 한다
    for n in ('소아청소년과', '내과', '이비인후과', '가정의학과', '정형외과'):
        assert n in names, n


def test_ev_restricted():
    r = other._ev_restricted
    assert r({'limitYn': 'Y', 'limitDetail': '입주민 전용'})
    assert r({'limitYn': 'Y', 'limitDetail': '거주자외 출입제한'})
    assert r({'limitYn': 'Y', 'limitDetail': ''})
    # 가능성만 말하는 안내는 제한으로 치지 않는다
    assert not r({'limitYn': 'Y', 'limitDetail': '시설 상황에 따라 이용이 제한될 수 있음'})
    assert not r({'limitYn': 'Y', 'limitDetail': '해당 시설 정책에 따라 이용이 불가할 수 있습니다.'})
    assert not r({'limitYn': 'Y', 'limitDetail': '해당차고지는 상용차 전용으로 승용차 이용에 제한이 있을수 있음'})
    assert not r({'limitYn': 'N', 'limitDetail': '입주민 전용'})
    assert not r({})


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_') and callable(fn):
            fn()
            print('ok', name)
