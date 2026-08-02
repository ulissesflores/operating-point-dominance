"""Protocol invariants that make the leakage-free claim checkable.

The properties the paper claims must hold by construction in the code: split sizes,
train-only scaler, cost reweighting and the absence of synthetic resampling.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "creditcard.csv"
CFG = json.loads((ROOT / "configs" / "run.json").read_text(encoding="utf-8"))

pytestmark = pytest.mark.skipif(not DATA.exists(), reason="dataset not downloaded")


@pytest.fixture(scope="module")
def splits():
    from sklearn.model_selection import train_test_split

    df = pd.read_csv(DATA)
    y = df["Class"].astype(int).values
    X = df.drop(columns=["Class"])
    X_tr, X_tmp, y_tr, y_tmp = train_test_split(
        X, y, test_size=0.30, random_state=42, stratify=y)
    X_va, X_te, y_va, y_te = train_test_split(
        X_tmp, y_tmp, test_size=0.50, random_state=42, stratify=y_tmp)
    return X_tr, X_va, X_te, y_tr, y_va, y_te


def test_split_sizes_match_original_run(splits):
    X_tr, X_va, X_te, *_ = splits
    assert len(X_tr) == 199364
    assert len(X_va) == 42721
    assert len(X_te) == 42722


def test_split_is_stratified(splits):
    _, _, _, y_tr, y_va, y_te = splits
    # 492 frauds split ~70/15/15
    assert y_tr.sum() == 344
    assert y_va.sum() == 74
    assert y_te.sum() == 74


def test_scaler_fit_on_train_only(splits):
    from sklearn.preprocessing import StandardScaler

    X_tr, X_va, X_te, *_ = splits
    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_te_s = scaler.transform(X_te)
    # train is exactly standardized; test is close but NOT exactly (no refit = no leakage)
    assert abs(X_tr_s.mean()) < 1e-10
    assert abs(X_te_s.mean()) > 1e-10


def test_pos_weight_matches_class_ratio(splits):
    _, _, _, y_tr, _, _ = splits
    neg = int((y_tr == 0).sum())
    pos = int((y_tr == 1).sum())
    pos_weight = neg / pos
    assert 570 < pos_weight < 585  # 199020/344 ~= 578.5


def test_no_smote_anywhere_in_pipeline():
    """The paper claims no synthetic resampling; the code must not import imblearn."""
    for script in (ROOT / "scripts").glob("*.py"):
        text = script.read_text(encoding="utf-8")
        assert "imblearn" not in text
        assert "SMOTE(" not in text
