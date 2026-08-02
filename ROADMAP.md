# Roadmap

What is planned, what it costs and what would have to be true for it to happen. Items are
ordered by what unblocks the most; nothing here is a promise of a date.

## Next re-run of the experiment (pays the declared debt in one shot)

The seven scripts, the configs and the outputs are sealed by
`runs/20260704T204343Z/checksums.sha256`. Anything that requires editing a sealed script is
**deliberately deferred to a re-run**, because patching it out of band would break the
data-to-results chain (see [`CHANGELOG.md`](CHANGELOG.md) § declared debt). A single re-run
closes all of it:

- Remove the dead `datahub.io` mirror from `scripts/get_data.py` (the primary mirror answers `200`,
  so replication is unaffected today).
- Docstring coverage from 50% (41/82) to 100%, and the 13 `ruff` findings, both reported by the
  informational CI job rather than enforced.
- `scripts/make_run.py` hardcodes the authoring repository in the manifest's `git.repository_url`,
  so the sealed record still names the private path where the experiment ran on 2026-07-04, and the
  project slug still carries a date. Both become the public name from the next run on.

**Cost, measured rather than guessed:** a full re-run reproduces 742 of the 743 fields of
`output/results.json` identically (only `runtime_seconds` moves) and the 7 PNGs bit-for-bit, so the
re-run buys hygiene, not science — which is exactly why it is scheduled rather than urgent. The
expensive step is the 20-seed study (~25 min CPU).

## Zero-setup replication notebook (`colab/replication.ipynb`)

A Colab notebook that installs the pinned environment, pulls the dataset with the SHA-256 check,
verifies the run manifest and reproduces the headline table without a local setup. The house
precedent is `blast-radius-containment`, whose notebook verifies its own hashes.

## External validation on a second benchmark

The paper's own direction (i): replicate the threshold-effect × architecture-effect decomposition
on a benchmark with a **temporal split** and a larger positive count (IEEE-CIS), also quantifying
the variance of threshold *selection*, which this package measures for training but not for
selection. This is a new study with its own repository, not a version of this one.

## Calibration coupled to explicit cost

Direction (ii): calibrate after cost reweighting (temperature scaling over the weighted loss) and
derive the threshold from declared business costs, closing the calibration-decision-governance
link. Requires the calibration pitfalls under extreme imbalance to be handled explicitly, so it is
a follow-up study rather than an increment here.

## Not planned

- **A leaderboard entry.** The ULB/Worldline benchmark is saturated and compromised as a
  leaderboard; this package uses it as a methodological instrument and says so in the paper.
- **A packaged library.** The code exists to make one study auditable, not to be depended on.
