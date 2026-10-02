# EQUILIBRIUM Planetary Resource Systems Core V1
## Storage Self-Loss Typed Physical Rate V1

Gate:

`EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1__STORAGE_SELF_LOSS_TYPED_PHYSICAL_RATE_V1`

This gate closes the raw storage self-loss ingress identified by the post-uncertainty core review.

The pinned predecessor core, typed-process closure, and end-to-end uncertainty successor are not rewritten. The closure is additive.

## Typed self-loss input

`self_loss` is now a required `QualifiedValue` rate in the successor storage path.

It must satisfy all of the following:

- layer equals `storage.layer`;
- quantity kind is `RATE`;
- interval equals `time_basis.interval_id`;
- value space is `PHYSICAL`;
- value is present;
- value is nonnegative.

Raw numeric self-loss is rejected before physical state transition.

## Storage equation

The nominal transition remains:

`s_next = s + dt * (eta_ch * charge - discharge / eta_dis - self_loss)`

The frozen predecessor function still performs the nominal arithmetic and capacity/rate checks after the successor validates and projects the typed self-loss value.

## Uncertainty

Self-loss enters storage uncertainty with coefficient:

`-dt`

The complete successor coefficient vector is:

- stock: `1`;
- charge: `dt * eta_ch`;
- discharge: `-dt / eta_dis`;
- self-loss: `-dt`.

Moment uncertainty still requires explicit covariance.

Empirical uncertainty still requires explicit sample alignment.

No zero-covariance assumption is introduced.

## Metadata

The output conservatively preserves and combines metadata from stock, charge, discharge, and self-loss:

- epistemic status;
- evidence refs;
- transform chain;
- hold codes;
- freshness;
- physical value space.

## Fail-closed conditions

The successor rejects:

- raw `Fraction` self-loss;
- negative self-loss;
- wrong layer;
- wrong quantity kind;
- interval mismatch;
- nonphysical/missing/conflicted self-loss through the existing QualifiedValue guard.

## Scope ceiling

This gate does not perform provider work, source ingestion, source fusion, aggregate EQ scoring, UI work, runtime admission, pointer promotion, global binding, or merge.
