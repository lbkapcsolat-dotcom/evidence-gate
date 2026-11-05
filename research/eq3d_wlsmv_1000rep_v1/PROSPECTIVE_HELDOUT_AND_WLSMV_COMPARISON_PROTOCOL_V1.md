# EQ3D M4/M5 Prospective Held-out Control + WLSMV Comparison Protocol V1

**Status: PROPOSED / PRE-REGISTRATION CANDIDATE ONLY. NO HELD-OUT RESULTS HAVE BEEN GENERATED.**

## Authority / traceability
- Predecessor draft PR #70 commit `42c6356bbcd5d44f574bfa60aa09073c8ed4970e`; the research branch remains independently unchanged.
- Canonical generator: `grid.R`, commit `d4efbe16e4124b332c4f20aa2dc548a299983cfa`, blob `674dacbc2813b26be3a4c8fa80c9560b115d5a0b`.
- Frozen historical grid: run 41586168086; 48 shard/12,000-row evidence. It is exclusively developmental evidence and **may not be relabeled held-out**.
- Bounded 8-fit fixture: run 41983775160; saved RDS audit run 41986568163. They too are developmental, **not held-out**.
- No changes to old 12,000 rows, m3_support labels, old CSV, historical thresholds, or original recruitment HOLD.

## Pre-specified prospective design
- Four synthetic truths: M3 positive reference, M4 boundary/overlap stress (NOT disjoint negative), M5 disjoint negative, M7 stress/disjoint negative *only after structural separation verified independently*.
- One separately approved **held-out batch**, nominal 250 attempts/truth = **1,000 attempts total**. N=4800 only, unless an external statistical reviewer approves an amended protocol **before any held-out results exist**. This N is a test setting, not a sample size recommendation.
- Freeze source blob, estimation options (WLSMV, theta, std.lv, lavaan 0.7.2), categorical thresholds, loadings, factor matrices, full output contract and a separate SHA256-tagged seed schedule before first observation.
- The seed namespace shall be independent of all original grid/8-fit fixture seeds. Generate each 32-bit seed as first 32 bits of SHA256 of `EQ3D_HELDOUT_V1|truth|rep|fixed_protocol_digest`, truncated into valid R integer range; reject any collision with original/test fixtures or within new batch. **Holdout fixture is not generated during protocol approval.**
- Strict temporal separation: protocol hash + code commit + seed schedule hash + registered analysis plan + external reviewer approval + explicit limited runtime authorization **before** generation. A change after inspection invalidates confirmatory status and requires a new held-out cohort.
- No optional stopping, substitutions, peeking, retry-until-PASS, altered truth labels or decision thresholds. Retry only documented infrastructure failures without changing seed/data; report all 1,000 planned attempts.

## Model admissibility and scientific classification
- Per fitted model preserve converged flag, optimizer diagnostics, finite fit measures, warnings, latently positive definite cov.lv, parameter SEs, gradient, Hessian/information rank tolerance and exact versions. Unknown or missing -> INSUFFICIENT_EVIDENCE; numerical invalidity -> INADMISSIBLE.
- Scientific output is three-way `M3_SUPPORTED_CANDIDATE`, `M3_REJECTED_CANDIDATE`, `INDETERMINATE`. Numerically inadmissible M3 is not automatically accepted as proof of a particular alternative. Comparator admissibility and structural separation are compulsory for a candidate rejection.
- M4 boundary case is **excluded from the disjoint-negative specificity denominator**; report boundary instability, rates of no-decision and warnings separately. Do not claim M4 vs M3 positive discrimination from that fixture.
- Preserve the previously declared 0.90 per-cell target **as a historical target**, not a newly justified significance threshold. New final decision criterion for confirmatory adoption is not approved by this spec; it requires independent review.
- Record per-truth, all-attempt denominators: correct classification, false acceptance on disjoint negatives, false rejection on positive M3, indeterminate, nonconvergence, covariance inadmissibility. Wilson 95% interval with all attempts; no exclusion of failed fits; report missing data explicitly. No cherry-picked conditional-on-OK rates.
- No presumption that a complete 1,000-rep held-out simulation constitutes empirical human-subject validation.

## WLSMV comparison protocol (fail-closed)
1. First verify both fitted lavaan objects use identical observed dataset, ordered variables, thresholds, N, estimator, parameterization, and supported test-statistic options. Reject mixed configurations.
2. Establish model nesting via independent structural demonstration and, if available in **pinned lavaan 0.7.2**, an explicit nesting test. **Do not infer nesting from the model name or larger/smaller df alone**; distinguish boundary cases.
3. For demonstrably nested, regular, admissible models only, assess whether the pinned lavaan version supports a suitable robust WLSMV difference test such as `lavTestLRT(..., method="satorra.2000")`, with version-appropriate arguments; inspect warnings and method/scale attributes, and verify prerequisites. Do not assume newer `check_nested` or `a_method` argument support in lavaan 0.7.2 without inspecting the installed function signature.
4. For nonnested or boundary/nonregular pairs, **do not report a chi-square difference test**; request a separately justified and pre-registered method or report descriptive fit metrics and INDETERMINATE. Simple subtraction of two `chisq.scaled` values is prohibited.
5. An undefined/failed robust comparison, negative/NaN scale factor, incompatible fits, failed covariance, invalid standard errors or unsupported nested relation yields HOLD_COMPARISON_METHOD, never a repaired p-value.

## Before activating any compute
- Scientific statistician signs off proposed errors/control definitions, held-out design, number of attempts, fit admissibility policy and version-specific robust comparison.
- Separate cost/CPU/time-bound human authorization. Do not enable an auto-on-merge workflow. No new model fitting or large grid is part of this PR.
- External evaluation on genuinely new data and measurement invariance assessment would be distinct gates before any empirical claim.

**Final: PASS_PROTOCOL_SPEC_AND_STATIC_NEGATIVES (if CI passes); HOLD_PROSPECTIVE_VALIDATION; NO_EMPIRICAL_VALIDATION / NO_GLOBAL_BIND / NO_PRODUCTION_ADMISSION.**
