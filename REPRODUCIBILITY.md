# Reproducibility

The step-by-step commands live in [`README.md`](README.md) (*Quick start* and
*Five-step replication protocol*). This file states what the seals actually
prove, what is reproducible and to what precision, and what cannot be changed
inside this package.

## Two seals, and why they are not the same guarantee

| Stage | What it is | What the seal proves |
|---|---|---|
| **Data** | `creditcard.csv` (284,807 transactions), maintained by ULB/Worldline and **not redistributed here** | **Identity.** `runs/20260704T204343Z/checksums-data.sha256` pins one SHA-256 (`76274b69…551a89`). `scripts/get_data.py` fetches from the public source and aborts on mismatch — so you compute on the same bytes the paper did, without this repository re-hosting third-party data. |
| **Derivation** | Everything computed *from* that file: `output/results.json`, raw scores, tables, figures, and every number in the paper | **Reproducibility.** Given the same data and a compatible environment, the pipeline regenerates the results; on the same platform it does so bit-for-bit (verified across two independent full executions). |

Conflating the two would over-claim. The dataset is **external and pinned**; the
derivation is **reproducible**.

## Verifying the published artifact without re-running anything

```bash
sha256sum -c runs/20260704T204343Z/checksums.sha256    # macOS: shasum -a 256 -c
```

37 files — the 7 scripts, `configs/run.json`, the run manifest, and all 28
outputs. Any edit to a sealed file without a fresh run makes this fail loudly.
The same check runs in CI on every push (`.github/workflows/ci.yml`), together
with the test suite and a syntax pass.

> **A legitimate re-run also makes this check fail — and that is not tampering.**
> Re-executing the pipeline rewrites the figure files, and PDF/SVG carry a
> creation timestamp (`/CreationDate`, `<dc:date>`) plus randomly generated
> matplotlib element IDs. A full re-run on this machine reported **15 of the 37
> as FAILED**, all of them figure files, with **zero** change in content: the 7
> PNGs stayed bit-identical, `output/results.json` differed in exactly one field
> out of 743 (`runtime_seconds`, wall-clock), and once the timestamp and the
> random IDs are normalised, 20 of the 21 vector files match byte for byte (the
> 21st only in the `id="image…"` attributes of its rasterised insets).
>
> So: run `sha256sum -c` **against the published artifact** to verify what was
> released. After your own re-run, compare *content* instead — `output/results.json`
> field by field (ignoring `runtime_seconds`) and the PNGs by hash. Reading 15
> `FAILED` lines as evidence of a doctored package would be the wrong conclusion.

## Determinism: the honest scope

Re-running steps 2–5 of the protocol **on the same platform** reproduces every
number bit-for-bit. That was verified by two independent full executions, and
the seed (42), the split, and every hyperparameter are fixed in
[`configs/run.json`](configs/run.json).

Bit-for-bit equality is **not** claimed across platforms: PyTorch and BLAS
kernels differ by CPU architecture and library build, which can move the last
decimals. What the paper claims is robust to that noise — the two-orders-of-
magnitude asymmetry (threshold +0.545 in F1 vs. architecture −0.007, whose 95%
paired-bootstrap interval [−0.055; +0.042] contains zero), the sign of every
delta, and the ordering of the four families.

## Environment

| File | Role |
|---|---|
| `requirements.txt` | Direct dependencies, exactly pinned. Enough to reproduce. |
| `requirements.lock` | Full transitive closure of the sealed run, generated verbatim from `environment.pip_freeze` in the run manifest (31 packages). Use it to match the original environment exactly. |

The published results were produced on **Python 3.11.15 (CPython), macOS-26.6
arm64**, recorded in `runs/20260704T204343Z/manifest.json`. CI additionally runs
the suite on Linux under Python 3.11 and 3.12.

Cost note: step 4 of the protocol (`multiseed_mlp.py --n-seeds 20`) is the
expensive one, ~25 min CPU, and is opt-in — `run_all.py` skips it unless asked.

## Test suite — 33 invariants

| File | Tests | Covers |
|---|---|---|
| `tests/test_data.py` | 3 | dataset SHA-256 anchor, shape and prevalence, column set |
| `tests/test_protocol.py` | 5 | split sizes and stratification, scaler fit on train only, `pos_weight` = class ratio, no SMOTE anywhere — the leakage classes are excluded by construction, and the tests assert it |
| `tests/test_results.py` | 10 | the thesis itself: threshold swing dominates, uncensored gap is a tie within noise, the censored-grid artifact, bootstrap block complete, closed-form prior shift vs. Monte Carlo, confusion matrices consistent with the reported metrics |
| `tests/test_metadata.py` | 2 | the version agrees across `CITATION.cff`, `.zenodo.json`, `codemeta.json` and `pyproject.toml`, and with the CHANGELOG — a three-of-four bump would ship an **immutable** Zenodo deposit showing the wrong version |
| `tests/test_export.py` | 13 | published-DOCX contract, checked on **both editions** (PT-BR and EN): page breaks, keep-together, bibliography style and hanging indent, no confidential strings — including the academic affiliation removed in 1.1.0 — figures numbered in mention order, and that the two editions are genuinely different documents |

## What cannot be fixed inside this package

`runs/20260704T204343Z/checksums.sha256` seals the scripts themselves. Editing a
sealed script without re-running the experiment breaks the data-to-results
chain, so the following are **declared debt, scheduled for the next re-run**
rather than patched out of band (see [`CHANGELOG.md`](CHANGELOG.md) § declared
debt):

- The dead `datahub.io` mirror in `scripts/get_data.py` (the primary mirror
  answers `200`; the script tries them in order, so replication is unaffected).
- Docstring coverage at 50% (41/82) and 13 `ruff` findings, reported by an
  informational CI job rather than enforced.
- `scripts/make_run.py` hardcodes the authoring repository in the manifest's
  `git.repository_url`, so the sealed run record names the private repository
  and internal path where the experiment was executed on 2026-07-04. That is the
  literal provenance of the seal, preserved verbatim rather than rewritten after
  the fact; the field will record this public repository from the next run on.
