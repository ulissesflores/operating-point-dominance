# Operating-Point Dominance in Credit-Card Fraud Detection

<!-- Zenodo DOI badge: insert after minting (Wave 2) -->
<!-- [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.TBD.svg)](https://doi.org/10.5281/zenodo.TBD) -->
[![License: Apache-2.0](https://img.shields.io/badge/code-Apache--2.0-blue.svg)](LICENSE)
[![License: CC BY 4.0](https://img.shields.io/badge/content-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](pyproject.toml)
[![Tests](https://img.shields.io/badge/tests-24%2F24-brightgreen.svg)](tests/)

*A confirmatory, auditable case study on the ULB/Worldline benchmark: how much of a fraud
detector's operational performance comes from the architecture — and how much from the
operating point.*

**Paper (Portuguese, APA 7):** [`docs/paper/paper-final.pdf`](docs/paper/paper-final.pdf) ·
[`docs/paper/paper-final.docx`](docs/paper/paper-final.docx)

## What this contributes

1. **An auditable decomposition of effects.** With a paired bootstrap (10,000 replicates)
   and a 20-seed training-variance study, moving the MLP decision threshold from the 0.5
   default to the validation optimum (τ\*=0.9994) shifts test F1 by **+0.545**
   (0.267 → 0.812), while switching from MLP to Logistic Regression shifts **−0.007**
   (95% CI [−0.055; +0.042]) — smaller than the MLP's own training standard deviation (0.016).
2. **Protocol forensics.** An apparent statistically significant MLP win
   (ΔF1 = +0.053, CI excluding zero) is shown to be an **artifact of the threshold grid
   truncated at 0.99** inherited from the precedent material; and that material's
   prevalence-robustness test is refuted (a resampling defect locked effective prevalence
   at ~0.2%).
3. **A leakage-free, bit-reproducible protocol:** scaler fitted on the training split only,
   cost reweighting (no synthetic oversampling), threshold selected on validation only,
   SHA-256-anchored data, determinism verified by identical re-execution, and protocol
   invariants covered by tests.

## Model at a glance

| Item | Value |
|---|---|
| Dataset | ULB/Worldline `creditcard.csv` (284,807 transactions; 0.173% fraud; SHA-256 `76274b69…a89`) |
| Split | Stratified 70/15/15, seed 42 (199,364 / 42,721 / 42,722) |
| Models | MLP 30-64-32-1 (BatchNorm, Dropout 0.2, pos_weight≈578.5) · balanced LR · Autoencoder · Isolation Forest |
| Threshold selection | Validation only; two regimes reported (censored v3.2 grid + uncensored PR-curve) |
| Inference | Paired bootstrap 10,000×; 20-seed retraining; closed-form prec(π) for prior shift |
| Determinism | Single-threaded + deterministic algorithms; two identical full runs |

## Quick start

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run_all.py            # downloads+verifies data, runs the experiment, figures, manifest
pytest tests/ -q             # 24 data/protocol/results/export invariants
```

What the seals prove, the honest scope of the determinism claim, and what cannot
be changed without a re-run: [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md).

## Five-step replication protocol

1. `python scripts/get_data.py` — downloads `creditcard.csv` (public mirror) and **verifies
   its SHA-256** against the original study's hash; aborts on mismatch.
   > **Mirror status (probed 2026-07-29).** Of the two mirrors listed in the script, the Google
   > Cloud Storage one answers `200`; `datahub.io` answers `404` and is a dead fallback. The
   > script tries them in order, so replication is unaffected. The dead entry is **left in place
   > on purpose**: `scripts/get_data.py` is sealed by `runs/20260704T204343Z/checksums.sha256`,
   > and editing it would break the run manifest without re-running the experiment. It is fixed
   > in the next re-run, not by an out-of-band edit.
2. `python scripts/run_experiment.py` — full protocol (4 models, 2 threshold regimes,
   paired bootstrap, closed-form prior-shift) → `output/results.json`.
3. `python scripts/verify_original_priorshift_bug.py` — forensic replay of both stress-test
   variants (defective vs. corrected) on the saved scores.
4. `python scripts/multiseed_mlp.py --n-seeds 20` — MLP training variance
   (~25 min CPU) → `output/multiseed_mlp.json`.
5. `python scripts/make_figures.py && (cd scripts && python make_run.py)` — vector figures
   (PDF+SVG) and the run contract (`runs/<id>/manifest.json` + `checksums.sha256`).

Re-running steps 2–5 on the same platform reproduces every number bit-for-bit
(verified across two independent full executions).

## Results (seed 42, test split)

| Model, threshold | Precision | Recall | F1 |
|---|---|---|---|
| MLP, 0.50 (default) | 0.157 | 0.878 | 0.267 |
| MLP, τ\*=0.9994 | 0.875 | 0.757 | **0.812** |
| LR, τ\*≈1.0 | 0.931 | 0.730 | **0.818** |
| Autoencoder, F1-optimal | 0.769 | 0.405 | 0.531 |
| Isolation Forest, F1-optimal | 0.112 | 0.459 | 0.179 |

ΔF1(MLP−LR) = −0.007 [−0.055; +0.042]; ΔAUC-PR = −0.046 [−0.111; +0.005] — both
indistinguishable from zero. MLP across 20 seeds: 0.814 ± 0.016 (the deterministic LR falls
inside the MLP's own distribution). Full numbers in [`output/results.json`](output/results.json).

## Layout

```
docs/paper/       paper-final.pdf + paper-final.docx (APA 7, Portuguese)
docs/source/      archival v3.2 notebook of the precedent study (SHA-256 131b5af0...)
configs/run.json  every hyperparameter and protocol contract
scripts/          experiment, multiseed, forensics, figures, manifest, hashing
tests/            24 invariants (data, anti-leakage protocol, results, export)
output/           results.json, raw scores (npz), CSV tables, PDF+SVG+PNG figures
runs/<id>/        manifest.json + checksums.sha256 (run contract)
schema/           manifest and dataset schemas
LICENSES/         Apache-2.0 (code) + CC-BY-4.0 (paper, figures) full texts
requirements.lock full environment of the sealed run (31 packages, verbatim)
```

## Citation

<!-- After minting the Zenodo DOI, update CITATION.cff and the BibTeX below. -->

```bibtex
@misc{flores2026operatingpoint,
  author = {Flores, Carlos Ulisses},
  title  = {O limiar importa mais que o modelo: domin{\^a}ncia do ponto de
            opera{\c c}{\~a}o na detec{\c c}{\~a}o de fraude em cart{\~o}es},
  year   = {2026},
  note   = {Codex Hash Research Laboratory},
  url    = {https://github.com/ulissesflores/operating-point-dominance},
}
```

Machine-readable metadata: [`CITATION.cff`](CITATION.cff) · [`codemeta.json`](codemeta.json) ·
[`.zenodo.json`](.zenodo.json).

## License

- **Code** (`scripts/`, `tests/`, `run_all.py`): [Apache-2.0](LICENSE)
- **Content** (paper, figures, documentation): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

## Anchor references

- Hayat & Magnier (2025). *Data leakage and deceptive performance…* — 10.3390/math13162563
- Abdelhamid & Desai (2024). *Balancing the scales…* — arXiv:2409.19751
- van den Goorbergh et al. (2022). *The harm of class imbalance corrections…* — 10.1093/jamia/ocac093
- Hand (2006). *Classifier technology and the illusion of progress* — 10.1214/088342306000000060
- Bouthillier et al. (2021). *Accounting for variance in ML benchmarks* — arXiv:2103.03098

## Contact

Carlos Ulisses Flores · Codex Hash Research Laboratory ·
ORCID [0000-0002-6034-7765](https://orcid.org/0000-0002-6034-7765) ·
[ulissesflores.com](https://ulissesflores.com)
