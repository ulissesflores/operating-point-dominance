"""Reproducible experiment pipeline — faithful reimplementation of the author's
notebook `estudo_caso_fraude_cartao_pytorch_v3p2_final_full.ipynb` (v3.2 FINAL),
plus a new paired-bootstrap analysis quantifying the MLP-vs-LR tie.

Scientific contract:
- The protocol reproduced here is what the CODE of v3.2 executes (cost-sensitive
  pos_weight, NO SMOTE, NO probability calibration, threshold grid capped at 0.99),
  not what the inherited prose claimed. See docs/paper/F1-GENESE.md.
- Every number quoted in the paper must come from output/results.json produced here.
- Determinism: fixed seeds + single-threaded torch + deterministic algorithms, so a
  re-run reproduces byte-identical metrics on the same platform.

Usage: .venv/bin/python scripts/run_experiment.py [--config configs/run.json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    """Stream a file through SHA-256 and return the hex digest."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def load_config(path: Path) -> dict:
    """Load the run configuration (JSON)."""
    return json.loads(path.read_text(encoding="utf-8"))


def set_all_seeds(seed: int) -> None:
    """Seed python, numpy and torch RNGs; force deterministic torch execution."""
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)


def build_mlp(in_features: int, hidden: tuple[int, ...], p_drop: float):
    """MLP identical to the v3.2 notebook: Linear->BatchNorm->ReLU->Dropout blocks."""
    from torch import nn

    layers: list = []
    prev = in_features
    for h in hidden:
        layers += [nn.Linear(prev, h), nn.BatchNorm1d(h), nn.ReLU(), nn.Dropout(p_drop)]
        prev = h
    layers += [nn.Linear(prev, 1)]
    return nn.Sequential(*layers)


def train_mlp(Xtr, ytr, Xva, yva, cfg: dict, log: list[str]):
    """Train the MLP with pos_weight cost reweighting; keep best state by F1@0.5 (val)."""
    import torch
    from sklearn.metrics import f1_score
    from torch import nn
    from torch.utils.data import DataLoader, TensorDataset

    model = build_mlp(Xtr.shape[1], tuple(cfg["hidden"]), cfg["p_drop"])
    pos = int((ytr == 1).sum())
    neg = int((ytr == 0).sum())
    pos_weight = torch.tensor([neg / max(pos, 1)], dtype=torch.float32)
    crit = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    opt = torch.optim.Adam(model.parameters(), lr=cfg["lr"])

    Xtr_t = torch.tensor(Xtr, dtype=torch.float32)
    ytr_t = torch.tensor(ytr, dtype=torch.float32).unsqueeze(1)
    Xva_t = torch.tensor(Xva, dtype=torch.float32)
    yva_t = torch.tensor(yva, dtype=torch.float32).unsqueeze(1)

    def pass_epoch(X_t, y_t, train: bool):
        ds = TensorDataset(X_t, y_t)
        dl = DataLoader(ds, batch_size=cfg["batch_size"], shuffle=train)
        tot = 0.0
        probs, gts = [], []
        model.train() if train else model.eval()
        for xb, yb in dl:
            with torch.set_grad_enabled(train):
                logits = model(xb)
                loss = crit(logits, yb)
                if train:
                    opt.zero_grad()
                    loss.backward()
                    opt.step()
            tot += loss.item() * xb.size(0)
            probs.append(torch.sigmoid(logits).detach().numpy())
            gts.append(yb.numpy())
        return tot / len(ds), np.vstack(gts).ravel().astype(int), np.vstack(probs).ravel()

    best, state = -1.0, None
    for ep in range(1, cfg["epochs"] + 1):
        tr_loss, _, _ = pass_epoch(Xtr_t, ytr_t, True)
        va_loss, yv, pv = pass_epoch(Xva_t, yva_t, False)
        f1 = f1_score(yv, (pv >= 0.5).astype(int), zero_division=0)
        if f1 > best:
            best = f1
            state = {k: v.clone() for k, v in model.state_dict().items()}
        if ep % 5 == 0 or ep == 1:
            line = f"[MLP ep {ep:03d}] loss_tr={tr_loss:.4f} loss_val={va_loss:.4f} F1@0.5_val={f1:.4f}"
            print(line)
            log.append(line)
    model.load_state_dict(state)
    model.eval()

    def predict(X):
        with torch.no_grad():
            t = torch.tensor(X, dtype=torch.float32)
            return torch.sigmoid(model(t)).numpy().ravel()

    return model, predict, {"pos_weight": neg / max(pos, 1), "best_f1_at_05_val": best}


def train_autoencoder(Xtr_norm, cfg: dict, log: list[str]):
    """Autoencoder trained on normal (negative) training rows only, as in v3.2."""
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, TensorDataset

    in_features = Xtr_norm.shape[1]
    b = cfg["bottleneck"]
    e1, e2 = cfg["encoder"]

    class AE(nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder = nn.Sequential(
                nn.Linear(in_features, e1), nn.ReLU(),
                nn.Linear(e1, e2), nn.ReLU(), nn.Linear(e2, b))
            self.decoder = nn.Sequential(
                nn.Linear(b, e2), nn.ReLU(),
                nn.Linear(e2, e1), nn.ReLU(), nn.Linear(e1, in_features))

        def forward(self, x):
            return self.decoder(self.encoder(x))

    model = AE()
    opt = torch.optim.Adam(model.parameters(), lr=cfg["lr"])
    crit = nn.MSELoss()
    X_t = torch.tensor(Xtr_norm, dtype=torch.float32)
    ds = TensorDataset(X_t)
    dl = DataLoader(ds, batch_size=cfg["batch_size"], shuffle=True)
    for ep in range(1, cfg["epochs"] + 1):
        model.train()
        tot = 0.0
        for (xb,) in dl:
            rec = model(xb)
            loss = crit(rec, xb)
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += loss.item() * xb.size(0)
        if ep % 10 == 0 or ep == 1:
            line = f"[AE ep {ep:03d}] loss_tr={tot / len(ds):.6f}"
            print(line)
            log.append(line)
    model.eval()

    def recon_error(X):
        with torch.no_grad():
            t = torch.tensor(X, dtype=torch.float32)
            rec = model(t).numpy()
        return ((rec - X) ** 2).mean(axis=1)

    return model, recon_error


def thresholds_from_probs(y_true, probs):
    """F1- and Fbeta2-optimal thresholds over the v3.2 grid (0.01..0.99, 99 points).

    NOTE: this grid is right-censored at 0.99 by design (fidelity to the original
    v3.2 notebook). Under pos_weight cost reweighting the score scale is inflated
    towards 1, so the F1 optimum may lie beyond the grid. The uncensored selection
    below (`uncensored_f1_threshold`) is the primary analysis; this one is kept as
    the fidelity-to-v3.2 variant.
    """
    from sklearn.metrics import f1_score, fbeta_score

    ths = np.linspace(0.01, 0.99, 99)
    f1s = [f1_score(y_true, (probs >= t).astype(int), zero_division=0) for t in ths]
    fb2s = [fbeta_score(y_true, (probs >= t).astype(int), beta=2, zero_division=0) for t in ths]
    return (float(ths[int(np.argmax(f1s))]), float(ths[int(np.argmax(fb2s))]),
            ths.tolist(), [float(v) for v in f1s])


def uncensored_f1_threshold(y_true, probs):
    """F1-optimal threshold over ALL candidate cutpoints of the validation PR curve
    (no grid censoring). Primary analysis: fixes the right-censoring artifact of the
    v3.2 grid flagged in the F2.5 statistical validation."""
    from sklearn.metrics import precision_recall_curve

    prec, rec, ths = precision_recall_curve(y_true, probs)
    # f1 for each threshold (prec/rec arrays have len(ths)+1; last point has no threshold)
    p, r = prec[:-1], rec[:-1]
    with np.errstate(divide="ignore", invalid="ignore"):
        f1 = np.where((p + r) > 0, 2 * p * r / (p + r), 0.0)
    i = int(np.argmax(f1))
    return float(ths[i]), float(f1[i])


def percentile_threshold(scores_val, y_val):
    """Percentile-grid threshold selection for score-based detectors (AE / IF)."""
    from sklearn.metrics import f1_score

    best, th = -1.0, None
    for p in np.linspace(50, 99.9, 80):
        t = np.percentile(scores_val, p)
        s = f1_score(y_val, (scores_val >= t).astype(int), zero_division=0)
        if s > best:
            best, th = s, float(t)
    return th


def eval_scores(y_true, scores, thr, name, cm_rows: list):
    """Metrics row + confusion-matrix row for one (model, threshold, split)."""
    from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                                 precision_score, recall_score)

    yhat = (scores >= thr).astype(int)
    y_true = y_true.astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, yhat).ravel()
    cm_rows.append({"model": name, "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)})
    return {"model": name,
            "accuracy": accuracy_score(y_true, yhat),
            "precision": precision_score(y_true, yhat, zero_division=0),
            "recall": recall_score(y_true, yhat, zero_division=0),
            "f1": f1_score(y_true, yhat, zero_division=0)}


def auc_metrics(y_true, scores):
    """AUC-ROC and AUC-PR (average precision) for a score vector."""
    from sklearn.metrics import average_precision_score, roc_auc_score

    return {"auc_roc": float(roc_auc_score(y_true, scores)),
            "auc_pr": float(average_precision_score(y_true, scores))}


def prior_shift_eval(scores, y_true, thr, ratio, name, rng):
    """Resample the test set (with replacement) to a target prevalence, as in v3.2."""
    from sklearn.metrics import (accuracy_score, f1_score, precision_score,
                                 recall_score)

    y_np = y_true.astype(int)
    n = len(y_np)
    idx_pos = np.where(y_np == 1)[0]
    idx_neg = np.where(y_np == 0)[0]
    n_pos = max(1, int(n * ratio))
    n_neg = n - n_pos
    sel = np.concatenate([
        rng.choice(idx_pos, size=n_pos, replace=len(idx_pos) < n_pos),
        rng.choice(idx_neg, size=min(n_neg, len(idx_neg)), replace=len(idx_neg) < n_neg)])
    rng.shuffle(sel)
    yhat = (scores[sel] >= thr).astype(int)
    ysel = y_np[sel]
    return {"model": name,
            "accuracy": accuracy_score(ysel, yhat),
            "precision": precision_score(ysel, yhat, zero_division=0),
            "recall": recall_score(ysel, yhat, zero_division=0),
            "f1": f1_score(ysel, yhat, zero_division=0),
            "pos_ratio": ratio}


def paired_bootstrap(y_true, probs_a, thr_a, probs_b, thr_b, n_rep, level, seed):
    """Paired bootstrap over test indices: F1 CIs per model, CI of the F1 difference,
    AND CI of the paired AUC-PR difference (F2.5 validation, statistical item 2).

    Scope (stated in the paper): percentile CIs capture TEST-SAMPLING variance
    conditional on the trained models and fixed thresholds — not training variance
    (measured separately by the multi-seed study) nor threshold-selection variance.
    With 74 positives the percentile CI is discrete/lumpy (declared limitation).
    """
    from sklearn.metrics import average_precision_score, f1_score

    rng = np.random.default_rng(seed)
    n = len(y_true)
    yhat_a = (probs_a >= thr_a).astype(int)
    yhat_b = (probs_b >= thr_b).astype(int)
    f1a, f1b, delta, apa, apb, dap = [], [], [], [], [], []
    for _ in range(n_rep):
        idx = rng.integers(0, n, size=n)
        ys = y_true[idx]
        if ys.sum() == 0:
            continue
        a = f1_score(ys, yhat_a[idx], zero_division=0)
        b = f1_score(ys, yhat_b[idx], zero_division=0)
        f1a.append(a)
        f1b.append(b)
        delta.append(a - b)
        pa = average_precision_score(ys, probs_a[idx])
        pb = average_precision_score(ys, probs_b[idx])
        apa.append(pa)
        apb.append(pb)
        dap.append(pa - pb)
    lo, hi = (1 - level) / 2 * 100, (1 + level) / 2 * 100

    def ci(v):
        return [float(np.percentile(v, lo)), float(np.percentile(v, hi))]

    delta = np.array(delta)
    dap = np.array(dap)
    return {
        "n_replicates_effective": len(delta),
        "f1_a_mean": float(np.mean(f1a)), "f1_a_ci": ci(f1a),
        "f1_b_mean": float(np.mean(f1b)), "f1_b_ci": ci(f1b),
        "delta_f1_mean": float(np.mean(delta)), "delta_f1_ci": ci(delta),
        "delta_f1_frac_positive": float((delta > 0).mean()),
        "auc_pr_a_mean": float(np.mean(apa)), "auc_pr_a_ci": ci(apa),
        "auc_pr_b_mean": float(np.mean(apb)), "auc_pr_b_ci": ci(apb),
        "delta_auc_pr_mean": float(np.mean(dap)), "delta_auc_pr_ci": ci(dap),
        "delta_auc_pr_frac_positive": float((dap > 0).mean()),
    }


def prior_shift_closed_form(y_true, scores, thr, ratios):
    """Analytical prior-shift sensitivity (F2.5 validation, statistical item 4).

    With a FIXED operating point, TPR and FPR are prevalence-invariant; precision
    and F1 under a new prior pi follow in closed form:
        prec(pi) = pi*TPR / (pi*TPR + (1-pi)*FPR)
        f1(pi)   = 2*prec*TPR / (prec + TPR)
    This replaces Monte-Carlo pseudo-replication of the 74 test positives with the
    identity it was simulating. Reading: mechanical metric sensitivity to prevalence
    at a fixed operating point — NOT performance under real distribution shift.
    """
    y = y_true.astype(int)
    yhat = (scores >= thr).astype(int)
    tp = int(((y == 1) & (yhat == 1)).sum())
    fn = int(((y == 1) & (yhat == 0)).sum())
    fp = int(((y == 0) & (yhat == 1)).sum())
    tn = int(((y == 0) & (yhat == 0)).sum())
    tpr = tp / (tp + fn) if tp + fn else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    rows = []
    for pi in ratios:
        prec = (pi * tpr) / (pi * tpr + (1 - pi) * fpr) if (pi * tpr + (1 - pi) * fpr) else 0.0
        f1 = 2 * prec * tpr / (prec + tpr) if (prec + tpr) else 0.0
        rows.append({"pi": pi, "precision": prec, "recall_tpr": tpr, "fpr": fpr, "f1": f1})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the fraud-detection experiment.")
    parser.add_argument("--config", type=Path, default=ROOT / "configs" / "run.json")
    args = parser.parse_args()
    cfg = load_config(args.config)
    log: list[str] = []
    t0 = time.time()

    # --- data integrity gate -------------------------------------------------
    data_path = ROOT / cfg["dataset"]["path"]
    digest = sha256_file(data_path)
    expected = cfg["dataset"]["sha256_expected"]
    if digest != expected:
        sys.exit(f"[FATAL] dataset sha256 mismatch: {digest} != {expected}")
    print(f"[OK] dataset sha256 verified: {digest}")

    set_all_seeds(cfg["seed"])

    df = pd.read_csv(data_path)
    assert df.shape == (cfg["dataset"]["n_rows_expected"], cfg["dataset"]["n_cols_expected"])
    y = df["Class"].astype(int).values
    X = df.drop(columns=["Class"])
    prevalence = float(y.mean())

    # --- split + scaling (fit on train only) ---------------------------------
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler

    X_tr, X_tmp, y_tr, y_tmp = train_test_split(
        X, y, test_size=cfg["split"]["test_size_tmp"], random_state=cfg["seed"], stratify=y)
    X_va, X_te, y_va, y_te = train_test_split(
        X_tmp, y_tmp, test_size=cfg["split"]["val_test_ratio"],
        random_state=cfg["seed"], stratify=y_tmp)

    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_va_s = scaler.transform(X_va)
    X_te_s = scaler.transform(X_te)

    # --- MLP ------------------------------------------------------------------
    from sklearn.metrics import fbeta_score

    _, mlp_predict, mlp_info = train_mlp(X_tr_s, y_tr, X_va_s, y_va, cfg["mlp"], log)
    p_va = mlp_predict(X_va_s)
    p_te = mlp_predict(X_te_s)
    t_f1, t_fb2, sweep_ths, sweep_f1_val = thresholds_from_probs(y_va, p_va)
    t_unc, f1_val_unc = uncensored_f1_threshold(y_va, p_va)
    sweep_f1_test = [float(__import__("sklearn.metrics", fromlist=["f1_score"]).f1_score(
        y_te, (p_te >= t).astype(int), zero_division=0)) for t in sweep_ths]
    print(f"Thresholds MLP: t_F1={t_f1:.2f} (grade v3.2) | t_Fb2={t_fb2:.2f} | "
          f"t_unc={t_unc:.6f} (sem censura)")

    cm_rows: list = []
    res_rows: list = []
    res_rows += [eval_scores(y_va, p_va, 0.5, "MLP_val@0.5", cm_rows),
                 eval_scores(y_te, p_te, 0.5, "MLP_test@0.5", cm_rows),
                 eval_scores(y_va, p_va, t_f1, f"MLP_val@{t_f1:.2f}", cm_rows),
                 eval_scores(y_te, p_te, t_f1, f"MLP_test@{t_f1:.2f}", cm_rows),
                 eval_scores(y_va, p_va, t_fb2, f"MLP_val@Fb2={t_fb2:.2f}", cm_rows),
                 eval_scores(y_te, p_te, t_fb2, f"MLP_test@Fb2={t_fb2:.2f}", cm_rows),
                 eval_scores(y_va, p_va, t_unc, "MLP_val@t*unc", cm_rows),
                 eval_scores(y_te, p_te, t_unc, "MLP_test@t*unc", cm_rows)]
    fb2_at_tfb2 = {
        "val": float(fbeta_score(y_va, (p_va >= t_fb2).astype(int), beta=2, zero_division=0)),
        "test": float(fbeta_score(y_te, (p_te >= t_fb2).astype(int), beta=2, zero_division=0)),
    }

    # --- Autoencoder (trained on negatives only) ------------------------------
    _, recon_error = train_autoencoder(X_tr_s[y_tr == 0], cfg["autoencoder"], log)
    err_va = recon_error(X_va_s)
    err_te = recon_error(X_te_s)
    th_ae = percentile_threshold(err_va, y_va)
    res_rows += [eval_scores(y_va, err_va, th_ae, "AE_val@F1", cm_rows),
                 eval_scores(y_te, err_te, th_ae, "AE_test@F1", cm_rows)]

    # --- Logistic Regression (balanced) ---------------------------------------
    from sklearn.linear_model import LogisticRegression

    lr = LogisticRegression(max_iter=cfg["logistic_regression"]["max_iter"],
                            class_weight=cfg["logistic_regression"]["class_weight"],
                            solver=cfg["logistic_regression"]["solver"])
    lr.fit(X_tr_s, y_tr)
    pr_va_lr = lr.predict_proba(X_va_s)[:, 1]
    pr_te_lr = lr.predict_proba(X_te_s)[:, 1]
    t_f1_lr, _, _, _ = thresholds_from_probs(y_va, pr_va_lr)
    t_unc_lr, f1_val_unc_lr = uncensored_f1_threshold(y_va, pr_va_lr)
    res_rows += [eval_scores(y_va, pr_va_lr, t_f1_lr, f"LR_val@{t_f1_lr:.2f}", cm_rows),
                 eval_scores(y_te, pr_te_lr, t_f1_lr, f"LR_test@{t_f1_lr:.2f}", cm_rows),
                 eval_scores(y_va, pr_va_lr, t_unc_lr, "LR_val@t*unc", cm_rows),
                 eval_scores(y_te, pr_te_lr, t_unc_lr, "LR_test@t*unc", cm_rows)]

    # --- Isolation Forest (trained on negatives only) --------------------------
    from sklearn.ensemble import IsolationForest

    iso = IsolationForest(n_estimators=cfg["isolation_forest"]["n_estimators"],
                          contamination=cfg["isolation_forest"]["contamination"],
                          random_state=cfg["isolation_forest"]["random_state"])
    iso.fit(X_tr_s[y_tr == 0])
    sc_va = -iso.score_samples(X_va_s)
    sc_te = -iso.score_samples(X_te_s)
    th_iso = percentile_threshold(sc_va, y_va)
    res_rows += [eval_scores(y_va, sc_va, th_iso, "IF_val@F1", cm_rows),
                 eval_scores(y_te, sc_te, th_iso, "IF_test@F1", cm_rows)]

    # --- AUC table --------------------------------------------------------------
    aucs = {
        "MLP_val": auc_metrics(y_va, p_va), "MLP_test": auc_metrics(y_te, p_te),
        "AE_val": auc_metrics(y_va, err_va), "AE_test": auc_metrics(y_te, err_te),
        "LR_val": auc_metrics(y_va, pr_va_lr), "LR_test": auc_metrics(y_te, pr_te_lr),
        "IF_val": auc_metrics(y_va, sc_va), "IF_test": auc_metrics(y_te, sc_te),
    }

    # --- prior-shift: closed-form analytical sensitivity (primary) + MC as check --
    ratios = cfg["prior_shift"]["ratios"]
    prior_closed = {
        "MLP": prior_shift_closed_form(y_te, p_te, t_f1, ratios),
        "LR": prior_shift_closed_form(y_te, pr_te_lr, t_f1_lr, ratios),
        "IF": prior_shift_closed_form(y_te, sc_te, th_iso, ratios),
    }
    rng = np.random.default_rng(cfg["seed"])
    stress_rows = []
    for r in ratios:
        stress_rows.append(prior_shift_eval(p_te, y_te, t_f1, r, f"MLP_prior_{r:.2f}@F1", rng))
        stress_rows.append(prior_shift_eval(pr_te_lr, y_te, t_f1_lr, r, f"LR_prior_{r:.2f}@F1", rng))
        stress_rows.append(prior_shift_eval(sc_te, y_te, th_iso, r, f"IF_prior_{r:.2f}@F1", rng))

    # --- permutation importance (MLP, validation) ---------------------------------
    from sklearn.inspection import permutation_importance

    class SkWrapper:
        """Sklearn-compatible thin wrapper around the trained MLP + threshold."""

        def __init__(self, predict_fn, thr):
            self.predict_fn = predict_fn
            self.thr = thr

        def fit(self, X, y=None):
            return self

        def predict(self, X):
            return (self.predict_fn(np.asarray(X)) >= self.thr).astype(int)

    pi = permutation_importance(
        SkWrapper(mlp_predict, t_f1), X_va_s, y_va, scoring="f1",
        n_repeats=cfg["permutation_importance"]["n_repeats"],
        random_state=cfg["permutation_importance"]["random_state"])
    imp = (pd.DataFrame({"feature": X.columns, "importance": pi.importances_mean,
                         "importance_std": pi.importances_std})
           .sort_values("importance", ascending=False).reset_index(drop=True))

    # --- paired bootstrap MLP vs LR (test), BOTH threshold regimes -----------------
    boot_censored = paired_bootstrap(
        y_te, p_te, t_f1, pr_te_lr, t_f1_lr,
        cfg["bootstrap"]["n_replicates"], cfg["bootstrap"]["level"],
        cfg["bootstrap"]["random_state"])
    boot_uncensored = paired_bootstrap(
        y_te, p_te, t_unc, pr_te_lr, t_unc_lr,
        cfg["bootstrap"]["n_replicates"], cfg["bootstrap"]["level"],
        cfg["bootstrap"]["random_state"])

    # --- persist everything -----------------------------------------------------
    tables = ROOT / "output" / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(res_rows).to_csv(tables / "table1_model_comparison.csv", index=False)
    pd.DataFrame(cm_rows).to_csv(tables / "table2_confusion_matrices.csv", index=False)
    pd.DataFrame(stress_rows).to_csv(tables / "table3_prior_shift.csv", index=False)
    imp.to_csv(tables / "table4_permutation_importance.csv", index=False)

    npz_dir = ROOT / "output"
    np.savez_compressed(
        npz_dir / "scores_test.npz",
        y_te=y_te, p_te_mlp=p_te, p_te_lr=pr_te_lr, err_te_ae=err_te, sc_te_if=sc_te,
        y_va=y_va, p_va_mlp=p_va, p_va_lr=pr_va_lr, err_va_ae=err_va, sc_va_if=sc_va)

    results = {
        "dataset": {"sha256": digest, "n_rows": int(df.shape[0]),
                    "prevalence": prevalence,
                    "split_sizes": {"train": int(len(y_tr)), "val": int(len(y_va)),
                                    "test": int(len(y_te))}},
        "seed": cfg["seed"],
        "mlp": {**mlp_info, "t_f1": t_f1, "t_fb2": t_fb2,
                "t_uncensored": t_unc, "f1_val_uncensored": f1_val_unc},
        "lr": {"t_f1": t_f1_lr, "t_uncensored": t_unc_lr,
               "f1_val_uncensored": f1_val_unc_lr},
        "ae": {"threshold": th_ae},
        "iforest": {"threshold": th_iso},
        "fbeta2_at_t_fb2": fb2_at_tfb2,
        "metrics": res_rows,
        "confusion_matrices": cm_rows,
        "auc": aucs,
        "prior_shift_closed_form": prior_closed,
        "prior_shift_montecarlo_check": stress_rows,
        "permutation_importance_top20": imp.head(20).to_dict(orient="records"),
        "threshold_sweep": {"thresholds": sweep_ths,
                            "f1_val_mlp": sweep_f1_val, "f1_test_mlp": sweep_f1_test},
        "bootstrap_mlp_vs_lr_test": {
            "censored_v32_grid": boot_censored,
            "uncensored_primary": boot_uncensored,
            "scope_note": ("percentile CIs; test-sampling variance conditional on "
                           "trained models and fixed thresholds; 74 unique positives "
                           "=> discrete/lumpy CI (declared limitation)"),
        },
        "runtime_seconds": round(time.time() - t0, 1),
        "train_log": log,
    }
    out = ROOT / "output" / "results.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[OK] results written: {out}")
    print(f"[OK] runtime: {results['runtime_seconds']}s")


if __name__ == "__main__":
    main()
