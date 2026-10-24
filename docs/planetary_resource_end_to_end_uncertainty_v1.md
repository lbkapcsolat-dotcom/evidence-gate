# EQUILIBRIUM Planetary Resource Systems Core V1
## End-to-End Uncertainty Propagation V1

Gate:

`EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1__END_TO_END_UNCERTAINTY_PROPAGATION_V1`

This gate adds an uncertainty-preserving successor boundary over the pinned core and the already-proven typed process-coupling path.

The predecessor Python/C++ core and typed-process artifacts remain byte-pinned.

## Balance path

The successor balance function returns one `QualifiedValue` per node.

Uncertainty is propagated across:
- production;
- demand;
- loss;
- internal flow through incidence coefficients;
- signed boundary flow;
- storage delta-rate;
- typed process contribution.

The nominal balance arithmetic is still validated by the typed process-aware predecessor path.

## Storage path

Storage uncertainty is propagated through the linearized V1 transition:

`s_next = s + dt * (eta_ch * u - w / eta_dis - self_loss_rate)`

The V1 `self_loss_rate` parameter remains deterministic and exact.

The uncertainty coefficients are:

- stock: `1`
- charge: `dt * eta_ch`
- discharge: `-dt / eta_dis`

## Uncertainty rules

`EXACT`
remains exact.

`INTERVAL`
propagates affinely with sign-safe bounds.

`MOMENT`
requires an explicit covariance matrix for the non-exact moment inputs.
No zero-covariance assumption is allowed.

`EMPIRICAL`
requires an explicit sample-alignment reference matching every empirical input.

`UNKNOWN`
remains unknown.

Mixed non-exact uncertainty families fail closed with `HOLD_UNCERTAINTY_OPERATOR`.

A non-exact input may never silently produce `ExactUncertainty`.

## Metadata preservation

Outputs preserve or conservatively carry forward:

- epistemic status, with IMPUTED dominating and otherwise DERIVED;
- evidence references;
- transform chains;
- hold codes;
- freshness summary;
- PHYSICAL value space.

Typed process contribution uncertainty and evidence participate in the same balance propagation.

## Scope ceiling

This gate does not perform provider work, source ingestion, source fusion, aggregate EQ scoring, UI work, runtime admission, pointer promotion, global binding, or merge.
