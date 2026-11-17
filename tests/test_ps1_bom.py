"""Windows PowerShell 5.1 把无 BOM 的 .ps1 按 ANSI 读，中文会乱码并报语法错。
所有含非 ASCII 字符的 .ps1 必须是 UTF-8 带 BOM。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_ps1_with_non_ascii_has_utf8_bom():
    bad = []
    for p in ROOT.glob('*.ps1'):
        b = p.read_bytes()
        if not b.isascii() and not b.startswith(b'\xef\xbb\xbf'):
            bad.append(p.name)
    assert not bad, f'缺 UTF-8 BOM：{bad}'
