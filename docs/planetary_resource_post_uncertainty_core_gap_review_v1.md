# EQUILIBRIUM Planetary Resource Systems Core V1
## Post-Uncertainty Core Gap Review V1

Gate:

`EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1__POST_UNCERTAINTY_CORE_GAP_REVIEW_V1`

This review starts from the pinned typed-process closure and end-to-end uncertainty successor. It performs no provider work and implements no new core capability.

## Remaining storage semantics

Capacity, charge/discharge rate limits, efficiency-domain checks, stock/rate separation, time-basis checks and successor uncertainty propagation remain proven.

The storage transition still has two bounded gaps:
- `storage.host_node_id` is not validated inside the local transition because topology context is absent;
- `self_loss_rate` remains a raw numeric rate parameter.

Capacity, max rates and efficiencies also remain exact manifest parameters rather than uncertainty-bearing parameters.

## Self-loss typing

`self_loss_rate` is the strongest remaining direct physical ingress gap.

It currently has no:
- UnitTag;
- interval_id;
- epistemic status;
- uncertainty;
- evidence refs;
- transform chain;
- ValueSpace.

The current function also accepts a negative self-loss. On the frozen fixture:

`baseline next stock = 104`

`self_loss_rate = -1 -> next stock = 105`

So a quantity semantically named a loss may currently increase stored stock.

The end-to-end uncertainty successor cannot include self-loss uncertainty or metadata because the input is a raw Fraction.

## Audit vector

L1-L4 remain separate and bounded.

Aggregate EQ scoring remains prohibited.

The audit vector is still a bare tuple without provenance or uncertainty metadata. This is not selected first because it does not currently enter the physical state transition.

## Boundary uncertainty

Boundary-flow uncertainty is complete for the current V1 flow path.

Boundary flows are QualifiedValue rates. Import/export directions supply explicit signs, and boundary uncertainty enters the end-to-end balance operator.

A review probe with a +5 import carrying interval uncertainty [-1,+1] and a matching exact demand preserves nominal residual 0 with output uncertainty [-1,+1].

BoundaryEdgeManifest itself remains topology metadata without separate evidence refs. Flow evidence remains attached to the QualifiedValue.

## Process metadata

The typed process successor preserves source, method, coefficient evidence, dimensional unit checks and activity metadata.

Remaining process qualification gaps:
- ProcessCoefficient has no coefficient uncertainty field;
- ProcessCoefficient has no explicit validity interval;
- coefficient uncertainty is therefore implicitly exact;
- ProcessManifest.manifest_version is not currently checked by the typed successor.

These are material future gaps, but they do not bypass the current typed physical boundary as directly as self-loss.

## Next single unproven capability

Selected:

`STORAGE_SELF_LOSS_TYPED_PHYSICAL_RATE_V1`

Reason:

Self-loss is the only reviewed term that directly changes physical stock while remaining completely outside QualifiedValue typing, uncertainty, evidence and non-negativity semantics.

This review does not implement the successor capability.
