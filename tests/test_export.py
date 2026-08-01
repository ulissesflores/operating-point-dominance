"""Export-contract smoke tests (audit finding A15): every published DOCX must obey
the house pagination/keep-together contract and carry no confidential strings.

Since v1.1.0 the package ships TWO editions (PT-BR and EN) side by side, so the
contract is checked per edition instead of only on the PT one — a regression in the
edition CI does not look at is a regression that ships.
"""

import base64
import re
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# (docx, page-break count, figure label) — the PT edition breaks before Resumo,
# Abstract, Introdução and Referências; the EN edition has no Resumo, so 3.
EDITIONS = [
    ("paper-final.docx", 4, "Figura"),
    ("paper-final-en.docx", 3, "Figure"),
]


def _docx(name: str) -> Path:
    path = ROOT / "docs" / "paper" / name
    if not path.exists():
        pytest.skip(f"export not built: {name}")
    return path


def _xml(docx: Path, name: str) -> str:
    with zipfile.ZipFile(docx) as z:
        return z.read(name).decode("utf-8")


@pytest.mark.parametrize("name,breaks,_fig", EDITIONS)
def test_page_breaks_on_headings(name, breaks, _fig):
    assert _xml(_docx(name), "word/document.xml").count("<w:pageBreakBefore/>") == breaks


@pytest.mark.parametrize("name,_breaks,_fig", EDITIONS)
def test_keep_together_applied(name, _breaks, _fig):
    doc = _xml(_docx(name), "word/document.xml")
    assert doc.count("<w:keepNext/>") >= 20  # caption labels/texts + table rows


@pytest.mark.parametrize("name,_breaks,_fig", EDITIONS)
def test_bibliography_style_no_bullets(name, _breaks, _fig):
    doc = _xml(_docx(name), "word/document.xml")
    head = "Referências" if name == "paper-final.docx" else "References"
    refs = doc[doc.find(head):]
    assert refs.count('w:val="Bibliography"') == 40  # 39 + auto-referência Flores (2026)
    assert "<w:numPr>" not in refs


@pytest.mark.parametrize("name,_breaks,_fig", EDITIONS)
def test_hanging_indent_in_style(name, _breaks, _fig):
    styles = _xml(_docx(name), "word/styles.xml")
    m = re.search(r'<w:style [^>]*w:styleId="Bibliography".*?</w:style>', styles, re.S)
    assert m and 'w:hanging="720"' in m.group(0)


# denylist kept base64-encoded so this public test file never carries the
# forbidden strings itself (they must not appear anywhere in the artifact).
# The last two are the academic affiliation: it leaked into the v1.0.1 cover and
# is what v1.1.0 removes — encoded here so CI can never let it back in.
_FORBIDDEN = [base64.b64decode(s).decode() for s in (
    "QUdUVQ==", "QW1lcmljYW4gR2xvYmFs",
    "TWVzdHJhbmRvIGVtIEludGVsaWfDqm5jaWEgQXJ0aWZpY2lhbA==",
    "TVNjIHN0dWRlbnQgaW4gQXJ0aWZpY2lhbCBJbnRlbGxpZ2VuY2U=",
)]


@pytest.mark.parametrize("name,_breaks,_fig", EDITIONS)
def test_no_confidential_strings_anywhere(name, _breaks, _fig):
    with zipfile.ZipFile(_docx(name)) as z:
        for member in z.namelist():
            blob = z.read(member).decode("utf-8", "ignore")
            assert not any(s in blob for s in _FORBIDDEN), f"{name}:{member}"


@pytest.mark.parametrize("name,_breaks,fig", EDITIONS)
def test_figures_numbered_in_mention_order(name, _breaks, fig):
    text = re.sub(r"<[^>]+>", "", _xml(_docx(name), "word/document.xml"))
    firsts: dict[int, int] = {}
    for m in re.finditer(rf"{fig} (\d+)", text):
        firsts.setdefault(int(m.group(1)), m.start())
    order = sorted(firsts, key=firsts.get)
    assert order == sorted(order), f"{name}: figuras fora da ordem de menção: {order}"


def test_both_editions_are_shipped():
    """A edição EN existe e não é a PT com outro nome (regressão de build silenciosa).

    O título PT PODE aparecer na edição EN — mas só dentro das referências, na
    auto-citação Flores (2026): o depósito Zenodo tem título PT e é imutável, então
    traduzi-lo ali seria citar uma obra que não existe. Fora das referências, não.
    """
    pt, en = _docx("paper-final.docx"), _docx("paper-final-en.docx")
    assert pt.read_bytes() != en.read_bytes()
    body = _xml(en, "word/document.xml")
    assert "Operating-point dominance in card fraud detection" in body
    before_refs = body[: body.find("References")]
    assert "dominância do ponto de operação" not in before_refs
