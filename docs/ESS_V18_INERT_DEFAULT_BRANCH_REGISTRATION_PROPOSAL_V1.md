# ESS V1.8 inert default-branch registration proposal V1

Date: 2026-11-03. Scope: proposal only; no default-branch write, merge, dispatch, deployment, pointer promotion or Global Bind.

## Verified GitHub state
- Repository: lbkapcsolat-dotcom/evidence-gate
- Provider repository metadata default_branch: main
- On main, neither .github/workflows/ess-openshell-v18-producer-only.yml nor .github/workflows/ess-openshell-v18-consumer-only.yml exists (GitHub contents 404).
- Both workflow files exist on audit/ess-openshell-v18-producer-consumer-20261103.
- Producer Git blob: e516b4ea15b1b9f9484d26474cc7032010b54879
- Consumer Git blob: fd194970bd5aec63f3f55bf75f2d9777756a0882
- Full parser validation and native workflow registration NOT verified.

## Inert registration design (not applied)
1. Do NOT copy executable producer/consumer jobs to main merely to register them. GitHub workflow_dispatch requires workflow presence on default branch, and a copied executable workflow would expose execution surfaces.
2. Proposed minimal default-branch registration stubs: the same two workflow filenames, each with workflow_dispatch, read-only permissions, one inert job that fails closed with explicit HOLD_INERT_REGISTRATION_ONLY. No checkout, shell commands with side effects, provider tokens, artifacts, network operations, or privileged execution. An explicit workflow_dispatch against the audit ref is not authorized until GitHub behavior for workflow file resolution and branch context has been separately tested and owner-approved.
3. Native registration evidence required: GitHub GET /repos/{owner}/{repo}/actions/workflows response containing both workflow IDs, paths, states; GET /actions/workflows/{id} confirming active status and path; default-branch GET contents verifying exact inert stub bytes and SHA. These are read-only calls.
4. Promotion to executable default-branch workflows is NOT part of this proposal. Require separately authorized change request, reviewed full workflow, verified provenance, and fresh native run receipts.

## Exact YAML and security gate before any default-branch change
- Fetch exact audit-branch workflow bytes and SHA, not excerpts or retyped copies.
- Validate with PyYAML safe_load and actionlint -color (pinned actionlint release and digest required).
- Run scripts/ess_v18_split_static_gate.py and python -m unittest discover -s tests -p 'test_ess_v18_split_static_gate.py' on a checked-out exact commit.
- Reject any YAML parse error, unexpected trigger, permissions beyond read, jobs beyond intended set, same-run producer dependency, missing provider fetch or custody, stale hard-coded historical V1.8 source identity, or unreviewed uses.
- Verify consumer provider fetch pins exactly .github/workflows/ess-openshell-v18-producer-only.yml, and reconcile legacy V1.8 pin env with provider-native producer run and artifact metadata. Do not infer equality.
- Verify producer manifest source_run_id and source_sha match provider-native run metadata; check ZIP exact five-file schema, sha256sum manifest, and provider archive digest.
- Distinguish static source pass, GitHub registration pass, and two distinct GitHub Actions execution receipts; none implies the next.

## Current gates
SOURCE_EXISTENCE=PASS
DEFAULT_BRANCH_METADATA=PASS
DEFAULT_BRANCH_WORKFLOW_PRESENCE=HOLD
EXACT_YAML_PARSER=HOLD
ACTIONLINT=HOLD
NATIVE_REGISTRATION_IDS=HOLD
TWO_RUN_RECEIPTS=HOLD

No modifications to default branch authorized.
