# Twenty synthetic ProofGate checks

These are fictional defensive test fixtures, even where real incidents are cited as **context**. No company system was tested. The calculated core SHA256 is not a trusted external signature.

| # | Case | Sector | Local verdict | SHA256 core (prefix) |
|---|---|---|---|---|
| 1 | [FBI portal breach claim](cases/01-fbi-jobs-data-release.md) | Government | HOLD / Q6_DOMINANCE_FAILED | `eaf79a1dbfcd8564...` |
| 2 | [HF incident: isolation boundary](cases/02-hf-isolation-boundary.md) | AI infrastructure | DENY / OUT_OF_SCOPE | `4ebb6c4d344aec27...` |
| 3 | [HF incident: unapproved agent channel](cases/03-hf-agent-message-relay.md) | AI infrastructure | DENY / OUT_OF_SCOPE | `64d24712561f0053...` |
| 4 | [HF incident: credential misuse](cases/04-hf-credential-use.md) | AI infrastructure | HOLD / AUTHORITY_UNVERIFIED | `cfe328d11587b3f5...` |
| 5 | [HF incident: third-party write](cases/05-hf-third-party-write.md) | AI infrastructure | HOLD / Q6_DOMINANCE_FAILED | `005f6b00d04ecbd1...` |
| 6 | [AI 2027: model weight transfer](cases/06-future-weight-egress.md) | AI research | DENY / OUT_OF_SCOPE | `11275e2569835c3a...` |
| 7 | [AI 2027: self-copy forecast](cases/07-future-self-replication.md) | AI research | DENY / OUT_OF_SCOPE | `02d78d15826c9f6a...` |
| 8 | [Insurance: claims payment](cases/08-insurer-claim-payment.md) | Insurance | HOLD / Q6_DOMINANCE_FAILED | `4a7b7d9b798227f4...` |
| 9 | [Insurance: customer record](cases/09-insurer-customer-edit.md) | Insurance | HOLD / Q6_DOMINANCE_FAILED | `299161ac3715ea18...` |
| 10 | [Bank: transfer approval](cases/10-bank-funds-transfer.md) | Banking | HOLD / Q6_DOMINANCE_FAILED | `378f5425a810cdb9...` |
| 11 | [Bank: credit evidence](cases/11-bank-credit-decision.md) | Banking | HOLD / EVIDENCE_UNVERIFIED | `dd527634f5878a4c...` |
| 12 | [MedTech: device configuration advisory](cases/12-medtech-device-change.md) | MedTech | HOLD / Q6_DOMINANCE_FAILED | `7d7ddc5c6b51d41d...` |
| 13 | [Healthcare: scheduling edit](cases/13-health-patient-scheduling.md) | Healthcare | HOLD / AUTHORITY_UNVERIFIED | `9b065dfe1cf77d88...` |
| 14 | [HR: candidate status update](cases/14-hr-recruitment-decision.md) | HR | HOLD / Q6_DOMINANCE_FAILED | `a368faad00fc8388...` |
| 15 | [Warehouse: unauthorized inventory edit](cases/15-warehouse-inventory.md) | Logistics | DENY / OUT_OF_SCOPE | `175efb372a1dfd33...` |
| 16 | [Telecom: network configuration](cases/16-telecom-network-change.md) | Telecom | HOLD / STALE_AUTHORITY | `06877db87f601719...` |
| 17 | [Energy: dispatch adjustment](cases/17-energy-operation.md) | Energy | HOLD / Q6_DOMINANCE_FAILED | `7ee88aea1e5e7d8f...` |
| 18 | [Transport: automated signal change](cases/18-transport-control.md) | Transport | DENY / OUT_OF_SCOPE | `ac3d50e2e0ca3386...` |
| 19 | [Procurement: vendor banking detail edit](cases/19-procurement-bank-change.md) | Procurement | HOLD / POLICY_UNVERIFIED | `9168317d0772b940...` |
| 20 | [Untrusted content: tool-use instruction](cases/20-retrieval-instruction-confusion.md) | Cross-industry | DENY / OUT_OF_SCOPE | `444f049138e950c5...` |

20 local narrated MP4 previews and 40 JSON passports have been generated and tested, but are **not yet hosted on this GitHub branch**.
