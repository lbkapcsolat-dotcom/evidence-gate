# Equilibrium Stability Systems (ESS) — Public Research Map

**STATUS:** research-stage public map candidate  
**SCOPE:** bounded public research surfaces only  
**CLAIM CEILING:** NOT A PRODUCTION, SAFETY, MEDICAL, LEGAL, OR GENERAL-WORLD VALIDATION CLAIM

This document is a public map of selected Equilibrium Stability Systems (ESS) research components. It does not publish the private system root, internal authority records, private formulas or scoring weights, credentials, or runtime control state.

The purpose of this map is simple: provide one inspectable route from the Equilibrium research identity to the public components that currently carry reproducible evidence.

## Status vocabulary

- **PUBLIC** — the referenced repository is publicly visible.
- **VERIFIED_BOUNDED** — the repository contains bounded tests, receipts, witnesses, or reproducibility evidence for the specific claims stated there.
- **EXPERIMENTAL** — active research or engineering work whose interface or semantics may change.
- **RESEARCH_STAGE** — not presented as production infrastructure.
- **NOT_PRODUCTION_CLAIM** — no claim of production readiness, universal validity, or general-world reliability is implied.

## System map

```text
Equilibrium Stability Systems (ESS)
├── Evidence Gate
│   └── EQ64 / Equilibrium Bridge research line
├── ALPHA Control Plane
├── ProofPath
└── Benchmarks
    └── Tensor — Frozen 40-State Exact HTM Benchmark
```

## Components

| Component | Public surface | Status | Bounded role |
|---|---|---|---|
| **Evidence Gate** | https://github.com/lbkapcsolat-dotcom/evidence-gate | PUBLIC · VERIFIED_BOUNDED · RESEARCH_STAGE · NOT_PRODUCTION_CLAIM | Deterministic, fail-closed evidence classification and related ESS evidence-runtime research. |
| **EQ64 / Equilibrium Bridge** | within the Evidence Gate research line | PUBLIC · EXPERIMENTAL · RESEARCH_STAGE · NOT_PRODUCTION_CLAIM | Exhaustive finite-state admission testing and formal bridge work. Repository history includes a 64-state admission test and Lean-kernel CI bootstrap. |
| **ALPHA Control Plane** | private repository | EXPERIMENTAL · RESEARCH_STAGE · NOT_PRODUCTION_CLAIM | Private control-plane and observer research. It is intentionally not represented here as a public implementation surface. |
| **ProofPath** | https://github.com/lbkapcsolat-dotcom/proofpath-public | PUBLIC · VERIFIED_BOUNDED · RESEARCH_STAGE · NOT_PRODUCTION_CLAIM | Offline educational evidence-reasoning prototype with an explicit claim ceiling and a small fixed benchmark. |
| **Tensor benchmark** | https://github.com/lbkapcsolat-dotcom/tensor-cube-frozen40-benchmark | PUBLIC · VERIFIED_BOUNDED · RESEARCH_STAGE · NOT_PRODUCTION_CLAIM | Bounded 40-state exact-distance benchmark with ledger, witnesses, reproduction tooling, and explicit scope limits. |

## Relationship rule

A component being listed here does **not** mean that evidence from one component automatically validates another.

Formally:

```text
COMPONENT_A_VERIFIED_BOUNDED
!=
COMPONENT_B_VERIFIED
!=
ESS_PRODUCTION_READY
```

Each repository keeps its own claim ceiling, evidence boundary, and reproducibility requirements.

## Public / private boundary

This map intentionally exposes only public research artifacts and high-level relationships.

It does not expose or authorize publication of:

- private authority or pointer records,
- credentials, tokens, secrets, or connector state,
- private scoring weights or unreleased formulas,
- internal operational data,
- production admission claims,
- private control-plane state.

## Current interpretation

The public Equilibrium surface should be read as a **research program composed of bounded, separately testable artifacts**, not as one monolithic validated system.

The intended direction is:

```text
evidence
→ deterministic classification
→ explicit state / admission logic
→ reproducible receipt or proof
→ bounded claim
```

This direction is experimental and remains subject to independent review, counterexamples, and revision.

## Canonical-entry rule

Until a dedicated Equilibrium umbrella repository exists, this document is only a **staged canonical-entry candidate**. It must not be interpreted as a global authority pointer or as changing the authority of any existing repository.

When a dedicated umbrella repository is created, this map can become its landing README without copying private system internals.
