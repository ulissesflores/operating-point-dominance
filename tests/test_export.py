"""Export-contract smoke tests (audit finding A15): the published DOCX must obey
the house pagination/keep-together contract and carry no confidential strings."""

import base64
import re
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DOCX = ROOT / "docs" / "paper" / "paper-final.docx"

pytestmark = pytest.mark.skipif(not DOCX.exists(), reason="export not built")


def _xml(name: str) -> str:
    with zipfile.ZipFile(DOCX) as z:
        return z.read(name).decode("utf-8")


def test_page_breaks_on_headings():
    doc = _xml("word/document.xml")
    assert doc.count("<w:pageBreakBefore/>") == 4  # Resumo, Abstract, Introdução, Referências


def test_keep_together_applied():
    doc = _xml("word/document.xml")
    assert doc.count("<w:keepNext/>") >= 20  # caption labels/texts + table rows


def test_bibliography_style_no_bullets():
    doc = _xml("word/document.xml")
    refs = doc[doc.find("Referências"):]
    assert refs.count('w:val="Bibliography"') == 39
    assert "<w:numPr>" not in refs


def test_hanging_indent_in_style():
    styles = _xml("word/styles.xml")
    m = re.search(r'<w:style [^>]*w:styleId="Bibliography".*?</w:style>', styles, re.S)
    assert m and 'w:hanging="720"' in m.group(0)


# denylist kept base64-encoded so this public test file never carries the
# forbidden strings itself (they must not appear anywhere in the artifact)
_FORBIDDEN = [base64.b64decode(s).decode() for s in ("QUdUVQ==", "QW1lcmljYW4gR2xvYmFs")]


def test_no_confidential_strings_anywhere():
    with zipfile.ZipFile(DOCX) as z:
        for name in z.namelist():
            blob = z.read(name).decode("utf-8", "ignore")
            assert not any(s in blob for s in _FORBIDDEN), name


def test_figures_numbered_in_mention_order():
    doc = _xml("word/document.xml")
    text = re.sub(r"<[^>]+>", "", doc)
    firsts = {}
    for m in re.finditer(r"Figura (\d+)", text):
        firsts.setdefault(int(m.group(1)), m.start())
    order = sorted(firsts, key=firsts.get)
    assert order == sorted(order), f"figuras fora da ordem de menção: {order}"
