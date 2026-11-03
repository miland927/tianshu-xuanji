"""STATUS.md 是最容易被写歪的一份文档，所以只检查两件事：它在、且没漏掉「未验证」。"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

STATUS = ROOT / 'STATUS.md'


def test_exists():
    assert STATUS.exists(), '先跑 tools/status.py'


def test_has_timestamp_and_sections():
    t = STATUS.read_text(encoding='utf-8')
    assert re.search(r'自动生成于 \d{4}-\d{2}-\d{2}', t)
    assert '## 已验证' in t and '## 未验证' in t


def test_unverified_list_is_not_empty():
    """未验证清单不能被删空——那意味着这份文档开始只报喜了。"""
    t = STATUS.read_text(encoding='utf-8')
    for must in ('备案', '法务', '第三方校验'):
        assert must in t, must
