# EQUILIBRIUM Planetary Resource Systems Core V1
## Process Coefficient Uncertainty Propagation V1

Gate:

`EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1__PROCESS_COEFFICIENT_UNCERTAINTY_PROPAGATION_V1`

This gate closes the unrepresented process-coefficient uncertainty gap while preserving the pinned typed-process, end-to-end uncertainty, typed storage self-loss, and legacy core artifacts.

## Explicit coefficient uncertainty

The successor introduces `UncertainProcessCoefficient` with:

- layer;
- node_id;
- nominal coefficient;
- uncertainty;
- evidence_ref;
- coefficient_unit.

The nominal typed-process arithmetic and dimensional checks are still delegated to the already-proven typed process predecessor.

## Product uncertainty semantics

For process output:

`y = activity * coefficient`

the successor propagates uncertainty in both factors.

EXACT × EXACT:
EXACT.

One side EXACT:
scale the non-exact uncertainty by the exact nominal other factor.

INTERVAL × INTERVAL:
exact bilinear rectangle bounds are computed for the output perturbation.

EMPIRICAL × EMPIRICAL:
paired samplewise multiplication is allowed only with an explicit matching sample_alignment_ref.

MOMENT × MOMENT:
covariance alone is not mathematically sufficient for the exact variance of a product.
The successor therefore requires explicit covariance plus the third/fourth joint perturbation moments needed for exact `E[Z^2]-E[Z]^2`, where

`Z = c*dA + a*dC + dA*dC`.

Missing joint evidence fails closed.

UNKNOWN:
remains UNKNOWN.

Mixed non-exact uncertainty families:
fail closed.

Multiple uncertain coefficient rows targeting the same node:
fail closed until cross-coefficient covariance semantics are explicitly supplied.

## Evidence and metadata

The successor preserves:

- coefficient evidence refs;
- process source and method refs;
- dimensional coefficient-unit checks;
- activity epistemic status;
- activity evidence and transform chain;
- hold codes;
- freshness;
- PHYSICAL value space.

Joint-moment evidence, when used, is appended explicitly.

## End-to-end integration

The resulting typed process `QualifiedValue` can enter the already-proven end-to-end balance uncertainty path directly.

Coefficient uncertainty is therefore no longer silently treated as zero.

## Scope ceiling

No provider work, new source ingest, multi-source fusion, aggregate EQ score, UI, runtime admission, pointer promotion, global binding, or merge is authorized.
