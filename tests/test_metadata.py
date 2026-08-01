"""Packaging-metadata invariants.

The version of this package is written in four places. A release that bumps three
of them ships a Zenodo deposit displaying the wrong version — and a Zenodo deposit
is **immutable**, so there is no fixing it afterwards. These tests make the release
checklist self-enforcing instead of relying on the operator's memory.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _versions() -> dict[str, str]:
    cff = re.search(r'^version:\s*"?([^"\n]+)"?\s*$',
                    (ROOT / "CITATION.cff").read_text(encoding="utf-8"), re.M)
    pyproject = re.search(r'^version\s*=\s*"([^"]+)"',
                          (ROOT / "pyproject.toml").read_text(encoding="utf-8"), re.M)
    assert cff and pyproject
    return {
        "CITATION.cff": cff.group(1).strip(),
        "pyproject.toml": pyproject.group(1),
        ".zenodo.json": json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))["version"],
        "codemeta.json": json.loads((ROOT / "codemeta.json").read_text(encoding="utf-8"))["version"],
    }


def test_version_is_the_same_everywhere():
    v = _versions()
    assert len(set(v.values())) == 1, f"versões divergentes entre arquivos de metadado: {v}"


def test_changelog_agrees_with_the_declared_version():
    """O topo do CHANGELOG e o metadado têm de contar a mesma história.

    Enquanto a seção do topo estiver `Unreleased`, o metadado deve continuar na
    ÚLTIMA versão publicada — bumpar antes da release faria o pacote afirmar uma
    versão que não existe em lugar nenhum. Quando a seção do topo ganha data, é ela
    que o metadado tem de espelhar.
    """
    sections = re.findall(r"^## \[([^\]]+)\] — (.+)$",
                          (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), re.M)
    assert sections, "CHANGELOG sem seções de versão"
    declared = set(_versions().values()).pop()
    top_version, top_date = sections[0]
    if top_date.strip().lower() == "unreleased":
        assert len(sections) > 1, "CHANGELOG só tem uma seção, e ela é Unreleased"
        expected = sections[1][0]  # a última versão de fato publicada
    else:
        expected = top_version
    assert declared == expected, (
        f"metadado diz {declared}; CHANGELOG esperava {expected} "
        f"(topo: [{top_version}] — {top_date})")
