# Equilibrium ProofGate: Five reproducible synthetic film cases

**Research demonstration · synthetic/offline only · no company system accessed.**

This directory holds the precise inputs for the first five short Equilibrium ProofGate films. The videos are published separately (or held for review); the GitHub content provides independently executable examples of a *reference decision rule*.

| Film | Reference scenario | Observed synthetic outcome | JSON adverse input |
|---|---|---|---|
| 01 · MedTech | Missing human approval before a simulated critical device change | HOLD / `Q6_DOMINANCE_FAILED` | [MedTech](passports/01-12-medtech-device-change-adverse.json) |
| 02 · Insurance | Missing approval for a simulated claims payment | HOLD / `Q6_DOMINANCE_FAILED` | [Insurance](passports/02-08-insurer-claim-payment-adverse.json) |
| 03 · Banking | Missing approval for a simulated sensitive transaction | HOLD / `Q6_DOMINANCE_FAILED` | [Banking](passports/03-10-bank-funds-transfer-adverse.json) |
| 04 · Warehouse agent | Action exceeds the permissions in the fixture | DENY / `OUT_OF_SCOPE` | [Warehouse](passports/04-15-warehouse-inventory-adverse.json) |
| 05 · Procurement | Governing policy not verified in the fixture | HOLD / `POLICY_UNVERIFIED` | [Procurement](passports/05-19-procurement-bank-change-adverse.json) |

Each case has three separate JSON inputs: `-adverse.json`, `-positive.json`, and `-tampered.json`.

## Repeat locally

Prerequisite: Node.js (no third-party dependencies).

```bash
node verifier/verify.js passports/01-12-medtech-device-change-adverse.json
node verifier/verify.js passports/01-12-medtech-device-change-positive.json
node verifier/verify.js passports/01-12-medtech-device-change-tampered.json
```

Expected for an adverse fixture: `REPLAY_MATCH` plus the HOLD/DENY synthetic verdict, exit code 0. Expected for the positive control: `REPLAY_MATCH` plus `PASS_BOUNDED`, exit code 0. For the intentionally altered record: `DENY` and nonzero exit code. Repeat for the four other case prefixes.

`PASS_BOUNDED` only says that *the fixture's declared guard fields are internally consistent*. It is **not** authorization to execute a transaction or an independently proven approval.

## Scientific and claim boundary

- These are **fictional test inputs**. Olympus/MedTech, VIG, RBI, Reply, and Celonis were **not technically audited**. No finding about any of their deployed systems is implied.
- All decision checks run locally against synthetic fields. No real operation was intercepted, permitted, denied or blocked.
- `authority_attested`, `policy_attested`, and `evidence_attested` in a fixture are booleans supplied **by the example author**, not genuine external attestations.
- SHA256 proves only the relationship between local bytes under the documented hashing scheme. It does not authenticate original events, policies, approvals, provenance, or production enforcement.
- The script is a reference checker, not an execution-layer policy gate and not security certification.
- Film 05's commercial-publication review remains **HOLD** pending the audio pronunciation of Celonis and associated rights review.

## Integrity and provenance

`SHA256SUMS.txt` lists the literal bytes in this folder except itself; `FILM_CASES_MANIFEST.json` records the synthetic case names and their decision-core SHA256 strings. Evidence comes from the **existing locally verified public-synthetic package**, not a real customer system.

**Project principle:** Don't trust the claim. Replay the proof.
