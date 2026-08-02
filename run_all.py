"""One-command replication: data -> experiment -> forensics -> figures -> run manifest.

The multiseed study (step 4 of the replication protocol, ~25 min CPU) is opt-in via
--with-multiseed; everything else runs in a few minutes.

Usage: python run_all.py [--with-multiseed]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(script: str, *args: str, cwd: Path = ROOT) -> None:
    """Run one pipeline step and abort the whole replication if it fails.

    Parameters
    ----------
    script : str
        File name inside ``scripts/``.
    *args : str
        Arguments forwarded to that script.
    cwd : Path, optional
        Working directory for the subprocess.
    """
    cmd = [sys.executable, str(ROOT / "scripts" / script), *args]
    print(f"\n=== {script} {' '.join(args)}")
    subprocess.run(cmd, check=True, cwd=cwd)


def main() -> None:
    """Replicate the published run end to end, in the documented order."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-multiseed", action="store_true")
    args = parser.parse_args()

    run("get_data.py")
    run("run_experiment.py")
    run("verify_original_priorshift_bug.py")
    if args.with_multiseed:
        run("multiseed_mlp.py", "--n-seeds", "20")
    run("make_figures.py")
    # make_run.py resolves paths relative to its own parent, run it from scripts/
    subprocess.run([sys.executable, "make_run.py", "--note", "run_all replication"],
                   check=True, cwd=ROOT / "scripts")
    print("\n[OK] replicação completa — ver output/ e runs/")


if __name__ == "__main__":
    main()
