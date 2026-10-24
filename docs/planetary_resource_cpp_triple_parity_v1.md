# EQUILIBRIUM Planetary Resource Systems Core V1
## Independent C++23 Domain Kernel Contract and Triple-Parity Map

Gate:
`EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1__INDEPENDENT_CPP_DOMAIN_IMPLEMENTATION_AND_40_OF_40_X3_V1`

Predecessor:
`PASS_BOUNDED_NATIVE_HGRAPH_RUNTIME_BIND_40_OF_40_X2_CROSS_PARITY`

## Etap 1: frozen independence contract

The third lane is an independently authored C++23 implementation of the frozen V1 domain semantics.

It MUST NOT:
- import Python;
- invoke the Python reference implementation;
- invoke Python-authored HGraph operator bodies;
- parse prior expected-output files as an implementation shortcut;
- emit an aggregate Equilibrium score;
- bind real-world data;
- claim runtime admission.

It MAY:
- use the same published mathematical contract and V01-V40 test specification;
- use the same layer names, hold-code names, and test identifiers;
- be compiled and executed in the same GitHub Actions job as the other lanes.

## Three validation lanes

A = frozen Python reference.
B = Python-authored HGraph operators executing on native `_hgraph` C++ runtime.
C = independent C++23 domain kernel.

Acceptance:
- A = 40/40 semantic outcomes PASS;
- B = 40/40 semantic outcomes PASS;
- C = 40/40 semantic outcomes PASS;
- normalized semantic parity A=B=C for V01..V40.

This is `40/40 x3`, not byte identity of language-specific diagnostic strings.

## Frozen normalized semantic result map

V01 PASS
V02 ZERO_RESIDUAL
V03 ZERO_RESIDUAL
V04 ZERO_RESIDUAL
V05 ZERO_RESIDUAL
V06 ZERO_RESIDUAL
V07 STORAGE_104
V08 ZERO_RESIDUAL
V09 ZERO_RESIDUAL
V10 FOUR_LAYER_ZERO
V11 HOLD_MANIFEST_MISMATCH
V12 HOLD_BOUNDARY_DIRECTION
V13 NONZERO_RESIDUAL
V14 HOLD_UNIT_MISMATCH
V15 HOLD_UNIT_MISMATCH
V16 HOLD_HHV_LHV_BASIS_MISMATCH
V17 HOLD_TIME_BASIS_MISMATCH
V18 HOLD_STORAGE_CAPACITY
V19 HOLD_STORAGE_RATE
V20 HOLD_STORAGE_RATE
V21 HOLD_EFFICIENCY_DOMAIN
V22 HOLD_MISSING_INPUT
V23 HOLD_CONFLICTED_INPUT
V24 HOLD_STALE_INPUT
V25 HOLD_IMPUTED_FLAG_ERASED
V26 HOLD_COVARIANCE_REQUIRED
V27 HOLD_SAMPLE_ALIGNMENT_REQUIRED
V28 HOLD_DOUBLE_COUNT_LOSS
V29 HOLD_PROCESS_EVIDENCE
V30 HOLD_CAUSALITY
V31 HOLD_AUDIT_PHYSICAL_MIX
V32 HOLD_AUDIT_PHYSICAL_MIX
V33 HOLD_STRESS_PHYSICAL_MIX
V34 HOLD_AGGREGATE_SCORE_PROHIBITED
V35 HOLD_TOPOLOGY_CHANGED
V36 DETERMINISTIC_EQUAL
V37 PERMUTATION_INVARIANT
V38 ZERO_DISTINCT_MISSING
V39 ZERO_COUPLING
V40 HISTORY_INDEPENDENT

## Physical contract

For each resource layer k:

`r = p - d - loss + B q + D h + A(discharge-charge) + N z`

Internal incidence columns sum to zero.
Boundary flow is explicit and directed.
Missing is not zero.
Physical, stress, evidence, and audit spaces remain disjoint.
Process coefficients require evidence and physical semantics.
Storage transitions fail closed on rate, efficiency, or capacity violations.
Gas HHV/LHV bases cannot be silently mixed.

## Claim ceiling

Passing this gate would prove an independent C++23 implementation agrees with both existing lanes on the bounded V01-V40 synthetic contract.

It would NOT prove:
- real-world data validity;
- calibrated stress thresholds;
- aggregate Equilibrium scoring;
- forecasting;
- policy conclusions;
- production/runtime admission;
- merge/pointer/global bind.
