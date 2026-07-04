"""Data-integrity gates: the dataset on disk must be byte-identical to the one
the original v3.2 run hashed, and its shape/prevalence must match the paper."""

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "creditcard.csv"
CFG = json.loads((ROOT / "configs" / "run.json").read_text(encoding="utf-8"))

pytestmark = pytest.mark.skipif(not DATA.exists(), reason="dataset not downloaded")


def test_dataset_sha256_matches_original_run():
    h = hashlib.sha256()
    with DATA.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    assert h.hexdigest() == CFG["dataset"]["sha256_expected"]


def test_dataset_shape_and_prevalence():
    df = pd.read_csv(DATA)
    assert df.shape == (284807, 31)
    prev = df["Class"].mean()
    assert 0.0016 < prev < 0.0019  # ~0.173%
    assert int(df["Class"].sum()) == 492


def test_dataset_columns():
    df = pd.read_csv(DATA, nrows=5)
    expected = ["Time"] + [f"V{i}" for i in range(1, 29)] + ["Amount", "Class"]
    assert list(df.columns) == expected
