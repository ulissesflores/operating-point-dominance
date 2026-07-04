"""Forensic check: prove that the original notebook's prior-shift stress test
(cell 11 of v3.2) never reaches the nominal prevalences.

The original line is
    np.random.choice(idx_pos, size=min(n_pos, len(idx_pos)), replace=len(idx_pos) < n_pos)
The `min(...)` caps positives at len(idx_pos)=74 regardless of the target ratio,
so the "1%..20% prevalence" scenarios all keep true prevalence ~0.17-0.22%. This
script replays BOTH variants (buggy vs corrected) on the saved test scores and
prints the achieved prevalence + F1, demonstrating that the buggy variant
reproduces the original paper's flat-F1 artifact.

Usage: .venv/bin/python scripts/verify_original_priorshift_bug.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.metrics import f1_score

ROOT = Path(__file__).resolve().parent.parent


def eval_variant(scores, y, thr, ratio, rng, buggy: bool):
    """One prior-shift evaluation, in the buggy (v3.2) or corrected variant."""
    y = y.astype(int)
    n = len(y)
    idx_pos = np.where(y == 1)[0]
    idx_neg = np.where(y == 0)[0]
    n_pos = max(1, int(n * ratio))
    n_neg = n - n_pos
    size_pos = min(n_pos, len(idx_pos)) if buggy else n_pos
    sel = np.concatenate([
        rng.choice(idx_pos, size=size_pos, replace=len(idx_pos) < n_pos),
        rng.choice(idx_neg, size=min(n_neg, len(idx_neg)), replace=len(idx_neg) < n_neg)])
    rng.shuffle(sel)
    ysel = y[sel]
    yhat = (scores[sel] >= thr).astype(int)
    return {"target": ratio, "achieved_prevalence": float(ysel.mean()),
            "f1": float(f1_score(ysel, yhat, zero_division=0)), "n_pos_drawn": int(size_pos)}


def main() -> None:
    npz = np.load(ROOT / "output" / "scores_test.npz")
    results = json.loads((ROOT / "output" / "results.json").read_text(encoding="utf-8"))
    y_te = npz["y_te"]
    p_te = npz["p_te_mlp"]
    thr = results["mlp"]["t_f1"]

    report = {"buggy_v32": [], "corrected": []}
    for ratio in (0.01, 0.05, 0.10, 0.20):
        rng = np.random.default_rng(42)
        report["buggy_v32"].append(eval_variant(p_te, y_te, thr, ratio, rng, buggy=True))
        rng = np.random.default_rng(42)
        report["corrected"].append(eval_variant(p_te, y_te, thr, ratio, rng, buggy=False))

    print(f"{'variant':12s} {'target':>7s} {'achieved':>9s} {'n_pos':>6s} {'F1':>7s}")
    print("-" * 48)
    for variant, rows in report.items():
        for r in rows:
            print(f"{variant:12s} {r['target']:7.2f} {r['achieved_prevalence']:9.4f} "
                  f"{r['n_pos_drawn']:6d} {r['f1']:7.4f}")

    out = ROOT / "output" / "priorshift_bug_verification.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"\n[OK] written: {out}")


if __name__ == "__main__":
    main()
