# EQUILIBRIUM Integrated Axioms Core V1
## Dependency DAG, theorem proof obligations, and third implementation

Gate:
`EQUILIBRIUM__INTEGRATED_AXIOMS_CORE_V1__DEPENDENCY_DAG_THEOREM_PROOF_OBLIGATIONS_AND_THIRD_IMPLEMENTATION_V1`

Predecessor:
`DOC-309`

Scope:
bounded formal assurance only.

This gate freezes the minimized 13-rule primitive/meta kernel, retains AX09/AX11/AX12 as derived guards, and adds an explicit acyclic axiom/theorem dependency DAG. Proof obligations are machine-readable and fail closed on cycles, missing bases, support-edge mismatch, or backedges into primitive assumptions.

Three independently authored evaluators are required to agree:
1. Python
2. JavaScript / Node.js
3. Go

Parity surfaces:
- state classification
- complete axiom vector
- canonical receipt digest
- derived-axiom proof-obligation outcomes
- T1-T8 theorem-obligation outcomes

Derived bounded obligations:
- `AX16 -> AX09`
- `AX10 -> AX11`
- `AX07 & AX16 -> AX12`

Theorem support:
- T1 no exact promotion from partial: AX08
- T2 no independence from unknown provenance: AX05 + AX06
- T3 no stale lease revival: AX10 + AX11
- T4 no local-global false pass: AX16 + AX09
- T5 revocation dominates evidence: AX07 + AX12
- T6 bounded proof nonpromotion: AX14
- T7 fail-closed composition: AX13
- T8 state before decision: AX16

Claim ceiling:
- no empirical Choice Space validation
- no general logical proof outside the frozen bounded model
- no real PKI/provenance trust claim
- no runtime or production admission
- no pointer promotion
- no global bind
- no merge
