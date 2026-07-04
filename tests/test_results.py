"""Results-contract tests: every quantitative claim family the paper makes must
hold in output/results.json (numbers in prose == numbers in the run)."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "output" / "results.json"

pytestmark = pytest.mark.skipif(not RESULTS.exists(), reason="run not executed yet")


@pytest.fixture(scope="module")
def results():
    return json.loads(RESULTS.read_text(encoding="utf-8"))


def _metric(results, model):
    for m in results["metrics"]:
        if m["model"] == model:
            return m
    raise KeyError(model)


def test_thesis_threshold_swing_dominates(results):
    """Core claim: the F1 swing from fixing the operating point is an order of
    magnitude larger than the architecture gap, in BOTH threshold regimes."""
    mlp_05 = _metric(results, "MLP_test@0.5")["f1"]
    mlp_unc = _metric(results, "MLP_test@t*unc")["f1"]
    lr_unc = _metric(results, "LR_test@t*unc")["f1"]
    swing = mlp_unc - mlp_05
    gap = abs(mlp_unc - lr_unc)
    assert swing > 0.3, f"threshold swing too small: {swing}"
    assert swing > 10 * gap, f"swing {swing} does not dominate architecture gap {gap}"


def test_uncensored_gap_is_tie_within_noise(results):
    """Primary analysis: the paired-bootstrap CI of delta-F1 (uncensored thresholds)
    must include zero (the tie claim), and so must delta-AUC-PR."""
    b = results["bootstrap_mlp_vs_lr_test"]["uncensored_primary"]
    lo, hi = b["delta_f1_ci"]
    assert lo < 0 < hi, f"delta F1 CI excludes zero: [{lo}, {hi}]"
    lo2, hi2 = b["delta_auc_pr_ci"]
    assert lo2 < 0 < hi2, f"delta AUC-PR CI excludes zero: [{lo2}, {hi2}]"


def test_censored_artifact_documented(results):
    """The censored-grid variant (v3.2 fidelity) must exist so the paper can show
    that the apparent 'significant MLP win' is a grid-censoring artifact."""
    b = results["bootstrap_mlp_vs_lr_test"]["censored_v32_grid"]
    lo, hi = b["delta_f1_ci"]
    assert lo > 0, "expected the censored-grid delta to (spuriously) exclude zero"


def test_supervised_beat_unsupervised(results):
    mlp = _metric(results, "MLP_test@t*unc")["f1"]
    ae = _metric(results, "AE_test@F1")["f1"]
    iforest = _metric(results, "IF_test@F1")["f1"]
    assert mlp > ae > iforest or mlp > ae and mlp > iforest


def test_bootstrap_block_is_complete(results):
    for regime in ("censored_v32_grid", "uncensored_primary"):
        b = results["bootstrap_mlp_vs_lr_test"][regime]
        assert b["n_replicates_effective"] >= 9900
        lo, hi = b["delta_f1_ci"]
        assert lo < hi
    swing = (_metric(results, "MLP_test@t*unc")["f1"]
             - _metric(results, "MLP_test@0.5")["f1"])
    b = results["bootstrap_mlp_vs_lr_test"]["uncensored_primary"]
    assert (b["delta_f1_ci"][1] - b["delta_f1_ci"][0]) < swing


def test_prior_shift_closed_form_consistent_with_montecarlo(results):
    """The analytical F1(pi) must be close to the Monte-Carlo check at each pi."""
    closed = results["prior_shift_closed_form"]
    mc = results["prior_shift_montecarlo_check"]
    for name in ("MLP", "LR"):
        for row in closed[name]:
            pi = row["pi"]
            mc_row = [r for r in mc if r["model"] == f"{name}_prior_{pi:.2f}@F1"][0]
            assert abs(row["f1"] - mc_row["f1"]) < 0.03, (name, pi)


def test_confusion_matrices_consistent_with_metrics(results):
    """precision/recall recomputed from tn/fp/fn/tp must equal the metric rows."""
    cms = {c["model"]: c for c in results["confusion_matrices"]}
    for m in results["metrics"]:
        cm = cms[m["model"]]
        tp, fp, fn = cm["tp"], cm["fp"], cm["fn"]
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        assert abs(prec - m["precision"]) < 1e-9
        assert abs(rec - m["recall"]) < 1e-9


def test_corrected_prior_shift_reaches_nominal_prevalence():
    path = ROOT / "output" / "priorshift_bug_verification.json"
    if not path.exists():
        pytest.skip("verification script not run")
    rep = json.loads(path.read_text(encoding="utf-8"))
    for row in rep["corrected"]:
        assert abs(row["achieved_prevalence"] - row["target"]) < 0.001
    for row in rep["buggy_v32"]:
        assert row["achieved_prevalence"] < 0.005  # the bug: never leaves ~0.2%


def test_v14_dominates_permutation_importance(results):
    imp = results["permutation_importance_top20"]
    assert imp[0]["feature"] == "V14"
    assert imp[0]["importance"] > 2 * imp[1]["importance"]


def test_every_figure_has_pdf_and_svg():
    fig_dir = ROOT / "output" / "figures"
    if not fig_dir.exists():
        pytest.skip("figures not generated")
    pdfs = {p.stem for p in fig_dir.glob("*.pdf")}
    svgs = {p.stem for p in fig_dir.glob("*.svg")}
    assert pdfs == svgs and len(pdfs) >= 7
