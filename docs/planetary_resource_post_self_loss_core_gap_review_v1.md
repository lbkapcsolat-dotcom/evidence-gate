# EQUILIBRIUM Planetary Resource Systems Core V1
## Post-Self-Loss Core Gap Review V1

Gate:

`EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1__POST_SELF_LOSS_CORE_GAP_REVIEW_V1`

This review pins the typed-process closure, end-to-end uncertainty successor, and typed storage self-loss successor. It implements no new core capability.

## Storage host-node scope

The local storage transition still receives no active topology node set.

A StorageManifest with an arbitrary nonexistent host_node_id is therefore accepted by the local transition when all local physical checks pass.

This is a topology-binding gap, not currently a local arithmetic corruption.

## Storage parameter uncertainty

Capacity, maximum charge/discharge rates, eta_charge, and eta_discharge remain exact Fraction manifest parameters.

The current successor cannot attach uncertainty/evidence/validity to those parameters, so storage uncertainty currently treats them as exact constants.

## Process coefficient uncertainty

ProcessCoefficient is evidence-bound and dimensionally checked, but coefficient itself is a raw Fraction.

No coefficient uncertainty field exists.

The typed process successor propagates activity uncertainty only.

With exact activity, process output uncertainty is ExactUncertainty because coefficient uncertainty cannot be represented.

This is selected as the next single capability because the coefficient directly scales physical process contribution and therefore can understate the end-to-end uncertainty envelope.

## Process coefficient validity interval

ProcessCoefficient has no valid_from, valid_to, or interval_id field.

Time applicability therefore cannot yet be fail-closed at the coefficient level.

## Process manifest version

ProcessManifest carries manifest_version, but the typed successor does not enforce it against an expected active version.

A V99 process manifest can currently pass against V1 target nodes if all other checks succeed.

## Audit vector provenance

L1-L4 remain separate and aggregate EQ scoring remains prohibited.

The audit vector remains a bare tuple without evidence refs or uncertainty.

This is not selected first because it does not mutate physical state or physical uncertainty.

## Next single unproven capability

`PROCESS_COEFFICIENT_UNCERTAINTY_PROPAGATION_V1`

This review does not implement the successor capability.
