# EQ3D V1 | Independent Statistician Review Packet

**STATUS: REVIEW REQUEST, NOT INDEPENDENT REVIEW.** No reviewer signature or opinion is present. This packet does not authorize synthetic held-out generation.

## Exact subjects under examination
Repository: `lbkapcsolat-dotcom/evidence-gate`.
- Source grid.R: Git blob `674dacbc2813b26be3a4c8fa80c9560b115d5a0b`; raw SHA256 `eda14848607b60fd53bee529039fda9fc879237e89ae26ff013811f67cc9a8d9`.
- Prospective protocol SHA256 `3238787440744c55020c6350df252cfcb7842c1f02642bf657cbf113295fe5cd`.
- Held-out seed schedule SHA256 `5acd606a4030825ff69af56be8f377e67ed4b50184c6068b8becc011cf0d8b19`.
- Seed GitHub lock commit: `25ef5c6340c5d19386ff2a9e595f7e53c4d1818c`; current read-only branch at `47b07f7c27a2b22cf3749b737cf83a5b0c3ab91c`; source candidate PR #72.
- Historical 12,000-grid run `41586168086`; bounded eight-fit run `41983775160`; RDS numerical diagnostic `41986568163`; source scientific HOLD is unchanged.
- Seed-schedule production: 1000 planned seeds, M3/M4/M5/M7 × 250; collision-free against 12,002 historical entries per custody proof. Seed derivation is publicly accessible. This is not a secret holdout or blinded execution.

## Materials for methodological referee
1. Read generator `grid.R` and its ordinal WLSMV settings, `PROSPECTIVE_HELDOUT_AND_WLSMV_COMPARISON_PROTOCOL_V1.md`, `ADMISSIBILITY_NEGATIVE_CONTROL_SPEC_V1.md`, `INDEPENDENT_METHOD_REVIEW_DOSSIER_V1.md`, and locked seed CSV+manifest.
2. Verify whether M3↔M4 covariance overlap represents a nonregular/boundary case and whether M3↔M5 and M3↔M7 are mathematically nested, disjoint, or neither. Do not infer from fit indices alone.
3. Verify the actual installed lavaan 0.7.2 `lavTestLRT` interface. Determine which robust comparison is applicable to the intended exact WLSMV/ordered/parameterization/theta fit, including `a_method`, `scaled_shifted`, test statistic availability, scaled factor diagnostics, and limits. Method presence is not method approval. No independent chi-square subtraction.
4. Assess M4→M3 nonconvergence and ill-conditioning and M5→M3 converged but non-positive-definite `cov.lv` as numerical inadmissibility without biasing the comparison rule toward the development observations.
5. Critique selection criteria before any new samples: false acceptance (M5, conditional M7), false rejection (M3), indeterminate rate, boundary M4 outcomes, denominator=all attempts, Wilson intervals, multiplicity/power and required decision bounds. Historical 0.90 target is not independent prospective acceptance.
6. Check reproducibility of source, seed lock, sample N=4800, 250 attempts/truth, 1000-attempt limit, separation of development vs genuinely new held-out set, controls against optional stopping or peeking, and compute budget.

## Required external signed findings
Reviewer legal name and credentials; institutional affiliation; date; signed document identity; exact three SHA256 values and source commit; evidence underlying each finding; explicit ACCEPT/REJECT/HOLD separately for nestedness and robust WLSMV comparison, numerical admissibility and threshold policy; conflicts of interest; exceptions and reproduction instructions.

**No signed reviewer submission = HOLD_INDEPENDENT_METHOD_REVIEW.**
**No reviewed version-compatible pairwise robust test = HOLD_WLSMV_COMPARISON_METHOD.**
**No time/CPU/budget approval = HOLD_PROSPECTIVE_EXECUTION.**
A GitHub PR review of Python tests alone never substitutes scientific peer review.

## Reviewer falsification prompts
- Show a legal M4 vs M3 alternative parameterization, or falsify the claimed overlap.
- Show whether the 0.04 M5 tetrad is invariant to the assumed measurement design.
- Exhibit any M3/M5 or M3/M7 paired ordinal WLSMV comparison that violates equal data, test compatibility or nesting assumptions, or prove none exists.
- Quantify numerical tolerance dependence of the M4 Hessian rank and the M5 negative `cov.lv` eigenvalue.
- Challenge prespecified 250×4 design and error budget, and provide a fully specified alternative **before** opening held-out outcomes.

**Verdict ceiling:** PASS_PACKET_AND_API_INTROSPECTION only. HOLD_EXTERNAL_REVIEW / HOLD_SCIENTIFIC_COMPARISON / NO_HELDOUT_EXECUTION / NO_GLOBAL_BIND / NO_PRODUCTION.
