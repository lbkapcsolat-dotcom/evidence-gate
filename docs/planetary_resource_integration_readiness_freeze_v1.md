# EQUILIBRIUM Planetary Resource Systems Core V1
## Integration Readiness Freeze V1

Gate:

`EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1__INTEGRATION_READINESS_FREEZE_V1`

The core is frozen for the first integrated minimal planetary-core build.

Pinned surfaces:
- balance kernel;
- boundary flow;
- typed process coupling;
- process coefficient uncertainty;
- process coefficient validity;
- process manifest-version enforcement;
- typed storage self-loss;
- storage host-node topology bind;
- end-to-end uncertainty;
- generic source adapter;
- adapter conformance harness;
- three proven real-source bindings.

The source-adapter subsystem remains frozen. No new provider is ingested.

Deferred, explicitly nonblocking for the first integration:
- STORAGE_PARAMETER_UNCERTAINTY
- AUDIT_VECTOR_PROVENANCE_TYPING

Core-change policy:

`NO_NEW_CORE_GAP_WORK_UNLESS_INTEGRATION_FINDS_BREAKAGE`

Exactly one next target is declared:

`INTEGRATED_MINIMAL_PLANETARY_CORE_V1`

This freeze does not perform multi-source fusion, runtime admission, global binding, merge, UI work, aggregate EQ scoring, or provider implementation.
