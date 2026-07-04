"""Training-variance study (F2.5 validation, statistical item 3): retrain the MLP
under N seeds on the SAME fixed split/scaler and measure the distribution of test
F1 at the (per-seed) validation-selected uncensored threshold.

This turns claim C3 from a platform anecdote (n=2) into a measured quantity:
sigma(train) of the MLP on this platform, to be compared against the MLP-LR gap.
The LR is deterministic (liblinear) and does not vary with seed — its test F1 is
recorded once as the reference line.

Usage: .venv/bin/python scripts/multiseed_mlp.py [--n-seeds 20]
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def main(n_seeds: int) -> None:
    import torch
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import average_precision_score, f1_score
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler

    import run_experiment as rx

    cfg = rx.load_config(ROOT / "configs" / "run.json")
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)

    df = pd.read_csv(ROOT / cfg["dataset"]["path"])
    y = df["Class"].astype(int).values
    X = df.drop(columns=["Class"])

    # split/scaler FIXED at the canonical seed 42 — we isolate TRAINING variance
    X_tr, X_tmp, y_tr, y_tmp = train_test_split(
        X, y, test_size=0.30, random_state=42, stratify=y)
    X_va, X_te, y_va, y_te = train_test_split(
        X_tmp, y_tmp, test_size=0.50, random_state=42, stratify=y_tmp)
    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_va_s = scaler.transform(X_va)
    X_te_s = scaler.transform(X_te)

    lr = LogisticRegression(max_iter=200, class_weight="balanced", solver="liblinear")
    lr.fit(X_tr_s, y_tr)
    pr_va_lr = lr.predict_proba(X_va_s)[:, 1]
    pr_te_lr = lr.predict_proba(X_te_s)[:, 1]
    t_lr, _ = rx.uncensored_f1_threshold(y_va, pr_va_lr)
    f1_lr_test = float(f1_score(y_te, (pr_te_lr >= t_lr).astype(int), zero_division=0))

    rows = []
    for seed in range(1, n_seeds + 1):
        t0 = time.time()
        torch.manual_seed(seed)
        np.random.seed(seed)
        log: list[str] = []
        _, predict, info = rx.train_mlp(X_tr_s, y_tr, X_va_s, y_va, cfg["mlp"], log)
        p_va = predict(X_va_s)
        p_te = predict(X_te_s)
        t_unc, _ = rx.uncensored_f1_threshold(y_va, p_va)
        t_grid, _, _, _ = rx.thresholds_from_probs(y_va, p_va)
        rows.append({
            "seed": seed,
            "t_uncensored": t_unc,
            "f1_test_uncensored": float(f1_score(
                y_te, (p_te >= t_unc).astype(int), zero_division=0)),
            "t_grid_v32": t_grid,
            "f1_test_grid_v32": float(f1_score(
                y_te, (p_te >= t_grid).astype(int), zero_division=0)),
            "f1_test_at_0.5": float(f1_score(
                y_te, (p_te >= 0.5).astype(int), zero_division=0)),
            "auc_pr_test": float(average_precision_score(y_te, p_te)),
            "seconds": round(time.time() - t0, 1),
        })
        print(f"[seed {seed:02d}] f1_unc={rows[-1]['f1_test_uncensored']:.4f} "
              f"f1_grid={rows[-1]['f1_test_grid_v32']:.4f} "
              f"aucpr={rows[-1]['auc_pr_test']:.4f} ({rows[-1]['seconds']}s)")

    arr = np.array([r["f1_test_uncensored"] for r in rows])
    arr_g = np.array([r["f1_test_grid_v32"] for r in rows])
    arr_ap = np.array([r["auc_pr_test"] for r in rows])
    out = {
        "n_seeds": n_seeds,
        "protocol": "fixed split/scaler (seed 42); per-seed torch init + shuffling; "
                    "per-seed validation-selected thresholds",
        "lr_reference": {"t_uncensored": t_lr, "f1_test_uncensored": f1_lr_test},
        "mlp_f1_test_uncensored": {
            "mean": float(arr.mean()), "std": float(arr.std(ddof=1)),
            "min": float(arr.min()), "max": float(arr.max()),
            "range": float(arr.max() - arr.min())},
        "mlp_f1_test_grid_v32": {
            "mean": float(arr_g.mean()), "std": float(arr_g.std(ddof=1)),
            "min": float(arr_g.min()), "max": float(arr_g.max())},
        "mlp_auc_pr_test": {
            "mean": float(arr_ap.mean()), "std": float(arr_ap.std(ddof=1)),
            "min": float(arr_ap.min()), "max": float(arr_ap.max())},
        "gap_vs_lr_per_seed": [float(v - f1_lr_test) for v in arr],
        "seeds": rows,
    }
    path = ROOT / "output" / "multiseed_mlp.json"
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] {path}")
    print(f"MLP f1_unc: {arr.mean():.4f} ± {arr.std(ddof=1):.4f} "
          f"(range {arr.min():.4f}–{arr.max():.4f}) | LR ref: {f1_lr_test:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-seeds", type=int, default=20)
    args = parser.parse_args()
    main(args.n_seeds)
