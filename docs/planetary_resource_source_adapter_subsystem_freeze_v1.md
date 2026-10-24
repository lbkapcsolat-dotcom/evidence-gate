# EQUILIBRIUM Planetary Resource Systems Core V1
## Source Adapter Subsystem Freeze and Return to Core V1

Gate:

`EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1__SOURCE_ADAPTER_SUBSYSTEM_FREEZE_AND_RETURN_TO_CORE_V1`

This gate closes the source-adapter development phase without adding a new provider.

## Frozen subsystem

The following are pinned by exact SHA256:

- generic source-adapter contract;
- generic adapter implementation;
- proven water/electricity/gas bindings;
- generic 3-of-3 receipt-equality gate;
- provider-binding conformance schema;
- conformance harness;
- conformance tests;
- deterministic generic-adapter and conformance receipts.

The three proven source bindings remain:
- Environment Agency freshwater;
- Elexon electricity;
- ENTSOG natural gas.

## Future provider path

Every future provider must follow exactly:

`BINDING -> CONFORMANCE -> EMPIRICAL_ADMISSION`

A future provider may not bypass conformance and call empirical admission directly.

A future binding may not add:
- provider-specific balance equations;
- provider-specific physics engines;
- silent unit or heating-value conversions;
- unpinned raw source bytes.

Any change to the generic adapter or conformance interface requires a new explicit gate.

## Crude oil

The crude-oil canary remains deferred.

Resume only when:
1. admitting the first real crude-oil source; or
2. making a claim that all four V1 resource layers have real-world empirical coverage.

No crude-oil provider implementation is performed in this freeze gate.

## Return to core

Source-adapter subsystem work now stops.

The next development domain is the Planetary Resource Core itself.

This freeze does not authorize source fusion, aggregate scores, UI, runtime admission, pointer promotion, global binding, or merge.
