"""Generate the ENGLISH figures for the English edition of the paper.

Design constraint that dictates this file's shape: `scripts/make_figures.py` is
SEALED by `runs/20260704T204343Z/checksums.sha256`, so its PT-BR labels cannot be
edited without invalidating the data->results chain. This script therefore does
not copy it — it *imports* it and translates the strings on their way into
matplotlib, so both editions are rendered by the exact same plotting code from
the exact same sealed inputs (`output/results.json`, `output/scores_test.npz`).

Output goes to `output/figures-en/`, which is NOT a sealed path. That is the
house "replicated" invariant (metodo/regras/cadeia-de-proveniencia.md): no
write-target of replication tooling may intersect a sealed stage glob. Verify
after running: `shasum -c runs/20260704T204343Z/checksums.sha256` -> 0 failures.

Usage: .venv/bin/python scripts/make_figures_en.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib.axes import Axes

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_figures as mf  # noqa: E402  (sealed module — imported, never edited)

# Longest-first so composite strings are matched before their fragments. Values
# carry the EN decimal point, since the PT source hardcodes "0,5" / "0,01-0,99".
GLOSSARY: dict[str, str] = {
    "ΔF1 = F1(MLP) − F1(LR), bootstrap pareado do teste":
        "ΔF1 = F1(MLP) − F1(LR), paired bootstrap on test",
    "queda média de F1 ao permutar (validação)":
        "mean F1 drop under permutation (validation)",
    "prevalência π (ponto de operação fixo)": "prevalence π (fixed operating point)",
    "validação (grade 0,01–0,99)": "validation (grid 0.01–0.99)",
    "teste (grade 0,01–0,99)": "test (grid 0.01–0.99)",
    "teto da grade 0,99": "grid ceiling 0.99",
    "MLP teste @0,50 (default)": "MLP test @0.50 (default)",
    "MLP teste @": "MLP test @",
    "contagem (escala log)": "count (log scale)",
    "F1 (classe positiva)": "F1 (positive class)",
    "limiar de decisão": "decision threshold",
    "legítimas (0)": "legitimate (0)",
    "fraudes (1)": "frauds (1)",
    " sem censura ": " uncensored ",
    " (analítico)": " (analytic)",
    "default 0,5": "default 0.5",
    "prev. ": "pred. ",
    "real ": "true ",
    "IC 95%": "95% CI",
    "frequência": "frequency",
    "Precisão": "Precision",
}
_ORDER = sorted(GLOSSARY, key=len, reverse=True)

# `f"{v:,}".replace(",", ".")` in the sealed module reaches matplotlib already
# formatted as PT-BR thousands ("284.807"); EN wants "284,807".
# The `(?!0\.)` guard is load-bearing: without it this also matches "0.745" —
# every F1/AUC-PR/τ* is formatted `:.3f`/`:.4f` and lives in [0,1], so a leading
# "0." marks a decimal, never a thousands group. Dropping the guard silently
# rewrote "AUC-PR=0.745" as "AUC-PR=0,745" in the first run of this script.
_THOUSANDS = re.compile(r"(?<![\d.])(?!0\.)\d{1,3}(?:\.\d{3})+(?![\d.])")


def translate(value):
    """Translate strings (and lists/tuples of them) reaching a matplotlib call."""
    if isinstance(value, str):
        for pt in _ORDER:
            value = value.replace(pt, GLOSSARY[pt])
        return _THOUSANDS.sub(lambda m: m.group(0).replace(".", ","), value)
    if isinstance(value, (list, tuple)) and any(isinstance(v, str) for v in value):
        return type(value)(translate(v) for v in value)
    return value


def _wrap(name: str) -> None:
    original = getattr(Axes, name)

    def patched(self, *args, **kwargs):
        return original(self, *(translate(a) for a in args),
                        **{k: translate(v) for k, v in kwargs.items()})

    setattr(Axes, name, patched)


# Every Axes entry point through which the sealed module passes user-visible text.
for _m in ("set_xlabel", "set_ylabel", "set_title", "text", "annotate", "bar",
           "barh", "plot", "scatter", "axvline", "hist", "set_xticks", "set_yticks"):
    _wrap(_m)


def main() -> None:
    mf.FIG = mf.ROOT / "output" / "figures-en"
    mf.main()
    print(f"[OK] English figures -> {mf.FIG}")


if __name__ == "__main__":
    main()
