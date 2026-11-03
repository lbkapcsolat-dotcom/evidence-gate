# ESS OpenShell V1.8 | Verified Release Candidate Gate V1

Mode: ISOLATED_AUDIT_BRANCH_ONLY / FAIL_CLOSED / NO_MERGE / NO_DEPLOY / NO_GLOBAL_BIND
Candidate commit: 33abad962f418ccd1b4f509f19e4c28068dbb814
Audit branch: audit/ess-openshell-v18-phase1-invocation-20261103

## Exact source readback (GitHub native blob IDs)
- Live workflow: .github/workflows/ess-openshell-live-v1.yml | 49106a3ac2419d5814452f57faa72a21b3dac750
- Regression tests: tests/test_openshell_v18_phase1_invocation.py | f06db0f9cc1026b4c81cdb7811221fcb1da5591b
- Offline CI: .github/workflows/ess-openshell-v18-offline-regression.yml | 8a233593f186f5bf8abe7224b25c0aab47656662

## Source checks
- 9 regression methods present: STATIC_PASS (not executed)
- Native policy revision: sandbox-after-policy.json current_policy_version == 2: STATIC_PASS
- Native policy hash: sandbox-after-policy.json configuration_admission.policy_hash == pinned PH: STATIC_PASS
- Missing native policy fields: fail closed: STATIC_PASS
- Exactly one fresh candidate event (not only one distinct UID): STATIC_PASS
- Phase2 registry append after HOLD gate: STATIC_PASS
- Staged registry_count_after reflects pending append: STATIC_PASS

## Required provider-native evidence, not yet proven
1. GitHub Actions push-triggered run_id for candidate commit or subsequent equivalent tested commit.
2. Exact job_id, conclusion=success, complete logs with 'Ran 9 tests' and 'OK'.
3. Native sandbox-after-policy.json from fresh isolated OpenShell provider run; exact revision and policy hash checked against pinned values.
4. Exact native run/event UID, SHA256 of raw provider bytes, and signed or authenticated provenance where available.
5. Byte-verified producer source artifact and rehydration evidence; no substitution of historical or expired artifact.
6. End-to-end final receipt, with all required gates true and unchanged preexisting registry receipts.

## Current verdict
HOLD_VERIFIED_RELEASE_CANDIDATE
First missing proof: PROVIDER_NATIVE_OFFLINE_CI_RUN_ID_AND_SUCCESS_JOB_LOG
Independent blocker: FRESH_NATIVE_POLICY_RECEIPT_AND_SOURCE_ARTIFACT_READBACK
No claim of CI PASS, native policy PASS, production readiness, or global authority promotion.

## Operator path
1. Open GitHub Actions offline regression workflow on audit branch; use provider-native run/receipt.
2. After nine tests pass, run the separate controlled sandbox-native proof collection only with explicit owner authorization and confirmed provider prerequisites.
3. Re-read exact commit, jobs, logs, native policy bytes, artifact hashes, and registry receipts.
4. Promote to VERIFIED_RELEASE_CANDIDATE only if every required proof is complete and consistent.
