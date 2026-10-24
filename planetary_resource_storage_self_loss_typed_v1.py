from __future__ import annotations

from fractions import Fraction
from typing import Sequence

import equilibrium_planetary_resource_core_v1 as core
import planetary_resource_end_to_end_uncertainty_v1 as e2e


class TypedSelfLossHold(ValueError):
    def __init__(self, code: str, detail: str = ""):
        self.code = code
        super().__init__(f"{code}: {detail}" if detail else code)


def storage_transition_with_typed_self_loss(
    storage: core.StorageManifest,
    time_basis: core.TimeBasis,
    stock: core.QualifiedValue,
    charge: core.QualifiedValue,
    discharge: core.QualifiedValue,
    self_loss: core.QualifiedValue,
    *,
    covariance: Sequence[Sequence[Fraction]] | None = None,
    sample_alignment_ref: str | None = None,
) -> core.QualifiedValue:
    if not isinstance(self_loss, core.QualifiedValue):
        raise TypedSelfLossHold("HOLD_SELF_LOSS_TYPED_VALUE_REQUIRED")

    core.qualified_value_guard(
        self_loss, core.GuardPolicy.ALLOW_IMPUTED_WITH_FLAG
    )
    if (
        self_loss.unit.layer is not storage.layer
        or self_loss.unit.kind is not core.QuantityKind.RATE
    ):
        raise core.HoldError(core.HoldCode.HOLD_UNIT_MISMATCH)
    if self_loss.interval_id != time_basis.interval_id:
        raise core.HoldError(core.HoldCode.HOLD_TIME_BASIS_MISMATCH)

    core.ensure_same_rate_signature(
        [charge, discharge, self_loss],
        storage.layer,
        time_basis.interval_id,
    )
    if self_loss.value is None:
        raise core.HoldError(core.HoldCode.HOLD_MISSING_INPUT)
    if self_loss.value < 0:
        raise TypedSelfLossHold("HOLD_NEGATIVE_SELF_LOSS")

    numeric = core.storage_transition(
        storage,
        time_basis,
        stock,
        charge,
        discharge,
        self_loss_rate=self_loss.value,
    )

    values = [stock, charge, discharge, self_loss]
    coefficients = [
        Fraction(1),
        time_basis.delta_t * storage.eta_charge,
        -time_basis.delta_t / storage.eta_discharge,
        -time_basis.delta_t,
    ]
    uncertainty = e2e._linear_uncertainty(
        coefficients,
        values,
        covariance=covariance,
        sample_alignment_ref=sample_alignment_ref,
    )
    meta = e2e._metadata(values, "storage:self_loss_typed")

    return core.QualifiedValue(
        value=numeric.value,
        unit=stock.unit,
        interval_id=time_basis.interval_id,
        uncertainty=uncertainty,
        **meta,
    )
