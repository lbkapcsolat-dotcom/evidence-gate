# EQ3D M4/M5 admissibility-aware decision and control specification V1

**Status: PROPOSED ONLY. No adopted model-selection rule, no re-scoring of original 12,000 synthetic results.**

Evidence: canonical grid.R at commit `d4efbe16e4124b332c4f20aa2dc548a299983cfa` (blob `674dacbc2813b26be3a4c8fa80c9560b115d5a0b`); saved RDS GitHub run [41986568163](https://github.com/lbkapcsolat-dotcom/evidence-gate/actions/runs/41986568163). M4→M3 nonconvergent, covariance min eigen -617.53; M5→M3 convergent but covariance min eigen -0.38347. These are two bounded synthetic fixtures, not empirical validation.

## Fail-closed two-stage rule

A. **Numerical admissibility**, ternary: ADMISSIBLE_DIAGNOSTIC, INADMISSIBLE, INSUFFICIENT_EVIDENCE. Provenance, convergence, finite fit indices, positive-definite latent covariance and critical-warning classification are mandatory. Nonconvergence or indefinite covariance => INADMISSIBLE. Missing or non-finite evidence => INSUFFICIENT_EVIDENCE. Gradients, Hessian/information spectral ranks, SE checks are retained as independent diagnostics, never a retrospective threshold tuned to these fixtures.

B. **Control interpretation**, ternary: REJECT_M3_CANDIDATE, M3_NOT_REJECTED_CANDIDATE, INDETERMINATE. A structurally separated alternative with admissible alternative fit and inadmissible M3 may justify *bounded candidate* rejection; both admissible is NOT proof of correct selection; missing comparator => INDETERMINATE.

## Negative-control registry
- M3 positive reference: no saved M3-truth RDS in bounded run; HOLD.
- M4: generator has overlapping/boundary M3 representation; not a valid disjoint negative control; HOLD_BOUNDARY_CONTROL even if M3 numerical fit fails.
- M5: non-zero tetrad 0.04 violates M3 cross-block rank-one restriction. In the bounded sample, M3 cov.lv indefinite and M5 comparator admissible; REJECT_M3_CANDIDATE_BOUNDED_ONLY. This is not a validated population classification rate.
- M7: 12,000-grid results exist but no M7-truth RDS in bounded fixture; HOLD_DIRECT_RDS_CONTROL.

Do NOT subtract independently scaled WLSMV chi-square values for a significance test; validate compatible comparison procedure before use. No new numeric decision thresholds are authorized.

## Required tests and fences
- Nonconvergence always disqualifies; converged+indefinite covariance disqualifies.
- Missing provenance, comparator, warnings or covariance evidence must remain INSUFFICIENT / INDETERMINATE, not PASS or FAIL of truth model.
- M4 boundary overlap cannot count as success of disjoint negative-control detection.
- Existing 12,000 original attempts, archived CSVs and final receipt are immutable.
- Prospective adoption requires pre-registered held-out evaluation with numerical tolerance sensitivity, explicit model identifiability diagnostics and error-rate calibration.

Claim ceiling: BRANCH_LOCAL_PROPOSED_SPEC / NO_EMPIRICAL_VALIDATION / NO_GLOBAL_BIND / NO_PRODUCTION_ADMISSION / NO_RETROACTIVE_RESCORING.
