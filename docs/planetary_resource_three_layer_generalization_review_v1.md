# EQUILIBRIUM Planetary Resource Systems Core V1
## Three-Layer Canary Generalization Review V1

Gate:

`EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1__THREE_LAYER_CANARY_GENERALIZATION_REVIEW_V1`

This review compares the already-admitted freshwater, electricity, and natural-gas canaries. It ingests no new source.

## Shared adapter schema

All three canaries reduce to the same bounded pipeline:

1. capture exact raw source bytes;
2. verify raw SHA256;
3. bind provenance;
4. bind source semantics;
5. map one source field to one canonical variable;
6. apply any source-specific semantic/unit adapter;
7. apply the frozen canonical unit conversion;
8. map to one source-local node;
9. align to one explicit interval;
10. compute deterministic freshness at an explicit `as_of`;
11. declare uncertainty;
12. declare missingness;
13. call the same empirical admission validator;
14. emit a deterministic receipt.

The provider-specific layer stops before the core mathematical kernel. No provider needs its own balance equations or physics engine.

## Evidence from the three canaries

| Layer | Source form | Canonical result | Extra exception |
| --- | --- | --- | --- |
| Freshwater | 0.832 m3/s | m3/s | none for direct volume-rate |
| Electricity | 22557 MW | W_e | source metric semantics must remain bounded |
| Natural gas | 28669751 kWh/h | W_th | explicit GCV/HHV basis required |

The gas canary is the strongest exception test so far because it needed an evidence-backed semantic adapter before the unchanged empirical contract could accept the value.

## Layer-specific exceptions

Freshwater needs no additional conversion evidence for a direct `m3/s` flow source.

Electricity uses fixed dimensional conversion such as `MW -> W_e`, but the source metric meaning, for example demand versus generation, must remain explicit.

Natural gas requires heating-value-basis evidence whenever the source energy basis and the canonical HHV label must be reconciled. Volume-to-energy remains HOLD without calorific-value evidence.

Crude oil has one untested physical exception: many practical sources are volumetric. The core is mass-based, so a volumetric oil source would require explicit density and reference-temperature/condition evidence.

## Crude-oil decision

A crude-oil canary is **not required to establish the shared adapter architecture**.

The water, electricity, and gas canaries already demonstrate the common pipeline across:
- volume rate,
- electrical power,
- energy rate with explicit heating-value semantics.

A crude-oil canary **is required before either**:
- the first real crude-oil source is admitted, or
- the system claims real-world empirical coverage of all four V1 resource layers.

Therefore:

`DEFER_UNTIL_CRUDE_OIL_ADMISSION_OR_FOUR_LAYER_COVERAGE_CLAIM`

If later executed, the useful oil test should target the oil-specific exception, preferably a source that forces explicit volume-to-mass evidence. A trivial already-mass-based source would add less information.

## Scope ceiling

This review does not:
- ingest a new source;
- fuse the three existing sources;
- aggregate them;
- compute a cross-resource score;
- bind UI;
- admit runtime operation;
- promote pointers;
- globally bind or merge anything.
