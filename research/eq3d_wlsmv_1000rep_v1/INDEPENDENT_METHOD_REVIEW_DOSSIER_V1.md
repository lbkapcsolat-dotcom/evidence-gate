# EQ3D Prospective V1 | Independent Method Review & Admission Dossier

**Control state:** HOLD_EXTERNAL_METHOD_REVIEW. No independent reviewer acceptance recorded. No held-out data generation authorized.

## Frozen evidence
- Research generator pinned: `grid.R` git blob SHA1 `674dacbc2813b26be3a4c8fa80c9560b115d5a0b`, raw SHA256 `eda14848607b60fd53bee529039fda9fc879237e89ae26ff013811f67cc9a8d9`.
- Prospective method protocol raw SHA256 `3238787440744c55020c6350df252cfcb7842c1f02642bf657cbf113295fe5cd`.
- 1,000 prospective seeds (250 × 4 truths) versioned in `preregistered_v1/HELDOUT_SEED_SCHEDULE_V1.csv`, SHA256 `5acd606a4030825ff69af56be8f377e67ed4b50184c6068b8becc011cf0d8b19`.
- SHA256 derivation and independence verified against **12,002 historical and bounded-fixture seeds**. GitHub Actions [41990901240](https://github.com/lbkapcsolat-dotcom/evidence-gate/actions/runs/41990901240) SUCCESS; GitHub commit `25ef5c6340c5d19386ff2a9e595f7e53c4d1818c`. No simulation or R model fits performed by seed gate.
- Historical development data: 12,000 grid entries, run 41586168086; saved 8-fit diagnostic run 41983775160; saved RDS numerical audit 41986568163. These are **not held-out**.

## Required independent statistician review checklist (not yet signed)
1. Confirm the M3 positive-reference and M5 distinct negative-control hypotheses, population fit/identifiability diagnostics and the M4 overlapping boundary exception. Review whether M7 actually qualifies as a disjoint negative after algebraic verification.
2. Confirm categorical WLSMV / theta / std.lv / lavaan 0.7.2 compatibility, identical categorical thresholds and source options. Examine the installed `formals(lavTestLRT)` and scaling test outputs. Establish parameter/covariance nesting and regularity before any robust LRT; do not infer from df. Do not subtract scaled chi-squares directly.
3. Reassess ill-conditioned Hessian/information, numerical rank tolerance sensitivity, boundary conditions, positive definiteness of `cov.lv`, warnings and the admissibility ternary classification without tuning to the original 12,000 or bounded 8 fits.
4. Confirm exact definitions of denominator (all attempts), M3 false rejection, negative-control false acceptance, indeterminate/failure, rates and 95% interval interpretation. Set an error-budget/decision threshold and multiplicity plan **before any held-out data**. The old 90% grid threshold alone does not establish new confirmatory power.
5. Independently review the 1,000-seed schedule hash, domain of R integer seeds, collision checks, data/analysis separation and control of potential peeking, retries, early stopping and source version drift.
6. Confirm need for a prospectively authorized limited compute budget and the consequences of scientific or numerical failure. Approve only specific resources, with no automatic workflow on merge.

## Missing external evidence (first missing proof)
- **Independent signed methodological review** (name/role, affiliation, timestamp, exact protocol/source/seed hashes, independent critique, acceptance or rejection): MISSING.
- **Verified lavaan 0.7.2 nested/robust comparison pathway on acceptable model pairs**: MISSING.
- **Final pre-registered adoption/error thresholds, with independent approval**: MISSING.
- **Explicit compute resource authorization**: MISSING.

## Review acceptance interface
An external reviewer may supply a signed document referring to all three exact SHA256 values and the GitHub commit. It should contain each checklist verdict with evidence and any remaining objections. A reviewer signature is never inferred from opening, commenting on or merging a PR. A document arriving after held-out generation cannot retroactively establish preregistration.

**State:** `PASS_SEED_SHA256_AND_PERSISTENCE` + `HOLD_INDEPENDENT_METHOD_REVIEW` + `HOLD_PROSPECTIVE_ADMISSION`.

Claims forbidden: EMPIRICAL_VALIDATION / GLOBAL_BIND / PRODUCTION_ADMISSION / PROSPECTIVE_RUNTIME_EXECUTION.
