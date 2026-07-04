"""Download creditcard.csv from a public mirror and verify its SHA-256 against the
hash recorded by the original study run. Aborts on mismatch — data integrity is a
precondition of every claim in the paper.

Usage: python scripts/get_data.py
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "configs" / "run.json").read_text(encoding="utf-8"))
DEST = ROOT / CFG["dataset"]["path"]
EXPECTED = CFG["dataset"]["sha256_expected"]
MIRRORS = [
    "https://storage.googleapis.com/download.tensorflow.org/data/creditcard.csv",
    "https://datahub.io/machine-learning/creditcard/r/creditcard.csv",
]


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    if DEST.exists() and sha256_file(DEST) == EXPECTED:
        print(f"[OK] dataset já presente e verificado: {DEST}")
        return
    for url in MIRRORS:
        try:
            print(f"[..] baixando {url}")
            urllib.request.urlretrieve(url, DEST)
            break
        except Exception as e:  # noqa: BLE001
            print(f"[WARN] {e}")
    digest = sha256_file(DEST)
    if digest != EXPECTED:
        sys.exit(f"[FATAL] sha256 divergente: {digest} != {EXPECTED}")
    print(f"[OK] dataset baixado e verificado: {DEST}\n[OK] sha256 {digest}")


if __name__ == "__main__":
    main()
