"""Generate every paper figure (PDF + SVG + PNG) from output/results.json and
output/scores_test.npz. No figure exists without a claim; each figure maps to a
specific claim in the paper (see the claim map below).

Claim map:
- fig1_class_distribution   -> rare-class setting (prevalence ~0.17%)
- fig2_pr_curves_test       -> PR-space comparison of the 4 models (supervised >> unsupervised)
- fig3_threshold_sweep      -> the thesis figure: F1 swing 0.21 -> ~0.75 from a single scalar
- fig4_confusion_shift      -> operational reading: FP collapse at the high operating point
- fig5_prior_shift          -> robustness to prevalence resampling (MLP/LR stable, IF flat-low)
- fig6_permutation_importance -> V14 dominance with correlation caveat
- fig7_bootstrap_delta      -> MLP-LR tie within noise (CI of the paired F1 difference)

Usage: .venv/bin/python scripts/make_figures.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "output" / "figures"


def save(fig, name: str) -> None:
    """Persist a figure as PDF + SVG + PNG with tight layout."""
    FIG.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    for ext in ("pdf", "svg", "png"):
        fig.savefig(FIG / f"{name}.{ext}", dpi=150)
    plt.close(fig)
    print(f"[OK] {name}.{{pdf,svg,png}}")


def main() -> None:
    results = json.loads((ROOT / "output" / "results.json").read_text(encoding="utf-8"))
    npz = np.load(ROOT / "output" / "scores_test.npz")
    y_te = npz["y_te"]

    # fig1 — class distribution (log scale; linear bars are unreadable at 0.17%)
    n_pos = int(y_te.sum())
    fig, ax = plt.subplots(figsize=(5.5, 3.4))
    counts = [int((y_te == 0).sum()), n_pos]
    ax.bar(["legítimas (0)", "fraudes (1)"], counts, color=["#4878a8", "#c44e52"],
           width=0.55)
    ax.set_yscale("log")
    ax.set_ylim(top=max(counts) * 12)  # headroom so labels never collide with the frame
    for i, v in enumerate(counts):
        ax.text(i, v * 1.6, f"{v:,}".replace(",", "."), ha="center", va="bottom",
                fontsize=10)
    ax.set_ylabel("contagem (escala log)")
    save(fig, "fig1_class_distribution")

    # fig2 — PR curves (test) for the 4 models
    from sklearn.metrics import average_precision_score, precision_recall_curve

    scores = {"MLP": npz["p_te_mlp"], "LR": npz["p_te_lr"],
              "Autoencoder": npz["err_te_ae"], "Isolation Forest": npz["sc_te_if"]}
    fig, ax = plt.subplots(figsize=(5.5, 4))
    for name, s in scores.items():
        p, r, _ = precision_recall_curve(y_te, s)
        ap = average_precision_score(y_te, s)
        ax.plot(r, p, label=f"{name} (AUC-PR={ap:.3f})", linewidth=1.6)
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precisão")
    ax.legend(fontsize=8, loc="lower left")
    save(fig, "fig2_pr_curves_test")

    # fig3 — THE thesis figure: F1 vs threshold (MLP val + test), grid sweep PLUS
    # the uncensored optimum marked as a point (primary regime, Section 6.1/6.2)
    from sklearn.metrics import f1_score as _f1

    sweep = results["threshold_sweep"]
    ths = np.array(sweep["thresholds"])
    f1v = np.array(sweep["f1_val_mlp"])
    f1t = np.array(sweep["f1_test_mlp"])
    t_grid = results["mlp"]["t_f1"]
    t_unc = results["mlp"]["t_uncensored"]
    p_te_mlp = npz["p_te_mlp"]
    f1_unc = float(_f1(y_te, (p_te_mlp >= t_unc).astype(int), zero_division=0))
    fig, ax = plt.subplots(figsize=(5.5, 4))
    ax.plot(ths, f1v, label="validação (grade 0,01–0,99)", linewidth=1.6)
    ax.plot(ths, f1t, label="teste (grade 0,01–0,99)", linewidth=1.6, linestyle="--")
    ax.axvline(0.5, color="gray", linestyle=":", linewidth=1)
    f1_05 = float(f1t[np.argmin(np.abs(ths - 0.5))])
    f1_sg = float(f1t[np.argmin(np.abs(ths - t_grid))])
    ax.annotate(f"default 0,5\nF1={f1_05:.3f}", xy=(0.5, f1_05),
                xytext=(0.53, f1_05 - 0.09), fontsize=8)
    ax.annotate(f"teto da grade 0,99\nF1={f1_sg:.3f}", xy=(t_grid, f1_sg),
                xytext=(t_grid - 0.34, f1_sg - 0.14), fontsize=8)
    ax.scatter([t_unc], [f1_unc], marker="*", s=140, color="#c44e52", zorder=5,
               label=f"τ*={t_unc:.4f} sem censura (F1={f1_unc:.3f})")
    ax.set_xlabel("limiar de decisão")
    ax.set_ylabel("F1 (classe positiva)")
    ax.legend(fontsize=7.5, loc="upper left")
    save(fig, "fig3_threshold_sweep")

    # fig4 — confusion shift at the two operating points (test): default 0.5 vs the
    # PRIMARY uncensored optimum (coherent with Section 6.1's FP 348 -> 8 reading)
    cms = {r["model"]: r for r in results["confusion_matrices"]}
    lo = cms["MLP_test@0.5"]
    hi = cms["MLP_test@t*unc"]
    fig, axes = plt.subplots(1, 2, figsize=(7, 3.2))
    for ax, cm, title in ((axes[0], lo, "MLP teste @0,50 (default)"),
                          (axes[1], hi, f"MLP teste @τ*={results['mlp']['t_uncensored']:.4f}")):
        m = np.array([[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]])
        ax.imshow(m, cmap="Blues", norm=matplotlib.colors.LogNorm(vmin=1, vmax=m.max()))
        for i in range(2):
            for j in range(2):
                ax.text(j, i, f"{m[i, j]:,}".replace(",", "."), ha="center", va="center",
                        fontsize=10, color="black")
        ax.set_title(title, fontsize=10)
        ax.set_xticks([0, 1], ["prev. 0", "prev. 1"])
        ax.set_yticks([0, 1], ["real 0", "real 1"])
    save(fig, "fig4_confusion_shift")

    # fig5 — analytical prior sensitivity at fixed operating point (+ MC check dots)
    closed = results["prior_shift_closed_form"]
    mc = results["prior_shift_montecarlo_check"]
    pis = np.linspace(0.001, 0.25, 200)
    fig, ax = plt.subplots(figsize=(5.5, 3.6))
    for name, style in (("MLP", "-"), ("LR", "--"), ("IF", ":")):
        tpr = closed[name][0]["recall_tpr"]
        fpr = closed[name][0]["fpr"]
        prec = pis * tpr / (pis * tpr + (1 - pis) * fpr)
        f1 = np.where(prec + tpr > 0, 2 * prec * tpr / (prec + tpr), 0)
        ax.plot(pis, f1, style, label=f"{name} (analítico)", linewidth=1.6)
        xs = [r["pos_ratio"] for r in mc if r["model"].startswith(name)]
        ys = [r["f1"] for r in mc if r["model"].startswith(name)]
        ax.scatter(xs, ys, s=18, zorder=3)
    ax.set_xlabel("prevalência π (ponto de operação fixo)")
    ax.set_ylabel("F1(π)")
    ax.set_ylim(0, 1)
    ax.legend(fontsize=8)
    save(fig, "fig5_prior_shift")

    # fig6 — permutation importance (top 20)
    imp = results["permutation_importance_top20"]
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    feats = [r["feature"] for r in imp][::-1]
    vals = [r["importance"] for r in imp][::-1]
    ax.barh(feats, vals, color="#4878a8")
    ax.set_xlabel("queda média de F1 ao permutar (validação)")
    save(fig, "fig6_permutation_importance")

    # fig7 — bootstrap distribution of the paired F1 difference (MLP - LR),
    # PRIMARY analysis: uncensored thresholds
    boot = results["bootstrap_mlp_vs_lr_test"]["uncensored_primary"]
    from sklearn.metrics import f1_score

    rng = np.random.default_rng(42)
    p_mlp = npz["p_te_mlp"]
    p_lr = npz["p_te_lr"]
    t_mlp = results["mlp"]["t_uncensored"]
    t_lr = results["lr"]["t_uncensored"]
    yhat_a = (p_mlp >= t_mlp).astype(int)
    yhat_b = (p_lr >= t_lr).astype(int)
    deltas = []
    n = len(y_te)
    for _ in range(4000):
        idx = rng.integers(0, n, size=n)
        ys = y_te[idx]
        if ys.sum() == 0:
            continue
        deltas.append(f1_score(ys, yhat_a[idx], zero_division=0)
                      - f1_score(ys, yhat_b[idx], zero_division=0))
    fig, ax = plt.subplots(figsize=(5.5, 3.6))
    ax.hist(deltas, bins=60, color="#4878a8", alpha=0.85)
    lo_ci, hi_ci = boot["delta_f1_ci"]  # CI from the uncensored primary analysis
    ax.axvline(0, color="black", linewidth=1)
    ax.axvline(lo_ci, color="#c44e52", linestyle="--", linewidth=1.2,
               label=f"IC 95% [{lo_ci:.3f}, {hi_ci:.3f}]")
    ax.axvline(hi_ci, color="#c44e52", linestyle="--", linewidth=1.2)
    ax.set_xlabel("ΔF1 = F1(MLP) − F1(LR), bootstrap pareado do teste")
    ax.set_ylabel("frequência")
    ax.legend(fontsize=8)
    save(fig, "fig7_bootstrap_delta")

    print("[OK] all figures generated")


if __name__ == "__main__":
    main()
