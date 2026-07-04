"""Assemble an audit-grade run directory: manifest.json + checksums.sha256.

A run is the atomic unit of scientific evidence. A run is valid only if
manifest.json validates against schema/manifest_schema.md AND checksums.sha256
exists and matches code + results (both hashed).

Usage: .venv/bin/python scripts/make_run.py --note "<why this run>"
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path

from hash_utils import environment_fingerprint, save_json, sha256_file

ROOT = Path(__file__).resolve().parent.parent


def get_git_commit_hash() -> str:
    """Current git HEAD, or UNKNOWN outside a repo."""
    try:
        return (subprocess.check_output(["git", "rev-parse", "HEAD"],
                                        stderr=subprocess.DEVNULL, cwd=ROOT)
                .decode("utf-8").strip())
    except Exception:
        return "UNKNOWN"


def main(note: str) -> None:
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = ROOT / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    cfg = json.loads((ROOT / "configs" / "run.json").read_text(encoding="utf-8"))
    results_path = ROOT / "output" / "results.json"
    results = json.loads(results_path.read_text(encoding="utf-8"))

    artifacts = {
        "code": sorted(str(p.relative_to(ROOT)) for p in (ROOT / "scripts").glob("*.py")),
        "config": ["configs/run.json"],
        "results": ["output/results.json", "output/scores_test.npz",
                    "output/priorshift_bug_verification.json"],
        "tables": sorted(str(p.relative_to(ROOT)) for p in (ROOT / "output" / "tables").glob("*.csv")),
        "figures": sorted(str(p.relative_to(ROOT))
                          for p in (ROOT / "output" / "figures").glob("*")
                          if p.suffix in (".pdf", ".svg", ".png")),
        "data": ["data/creditcard.csv"],
    }

    manifest = {
        "run_id": run_id,
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "git": {
            "repository_url": "https://github.com/ulissesflores/research-lab (fabrica/artigos/2025-fraud-detection-mlp)",
            "commit": get_git_commit_hash(),
            "tag": None,
        },
        "environment": environment_fingerprint(),
        "parameters": cfg,
        "dataset_sha256": results["dataset"]["sha256"],
        "artifacts": {k: v for k, v in artifacts.items() if k != "data"},
        "artifacts_external": {"data": artifacts["data"],
                               "note": "creditcard.csv is not committed (144 MB); "
                                       "integrity anchored by dataset_sha256"},
        "notes": note or "audit-grade run of the fraud-detection operating-point experiment",
    }
    save_json(manifest, run_dir / "manifest.json")

    rel_paths = [p for group in ("code", "config", "results", "tables", "figures")
                 for p in artifacts[group]]
    lines = [f"{sha256_file(ROOT / p)}  {p}" for p in rel_paths]
    lines.append(f"{sha256_file(run_dir / 'manifest.json')}  "
                 f"runs/{run_id}/manifest.json")
    (run_dir / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # data hash recorded separately (big file, hashed streamed)
    data_line = f"{sha256_file(ROOT / 'data' / 'creditcard.csv')}  data/creditcard.csv\n"
    (run_dir / "checksums-data.sha256").write_text(data_line, encoding="utf-8")

    print(f"[OK] run assembled: {run_dir}")
    print(f"[OK] manifest: {run_dir / 'manifest.json'}")
    print(f"[OK] checksums: {run_dir / 'checksums.sha256'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Assemble an audit-grade run directory.")
    parser.add_argument("--note", type=str, default="")
    args = parser.parse_args()
    main(args.note)
