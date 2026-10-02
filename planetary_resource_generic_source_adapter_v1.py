from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
from pathlib import Path
from typing import Tuple

import planetary_resource_empirical_admission_v1 as admission


@dataclass(frozen=True)
class PreContractTransform:
    enabled: bool = False
    from_unit: str = ""
    to_unit: str = ""
    factor_n: int = 1
    factor_d: int = 1
    to_gas_basis: str = ""
    evidence_ref: str = ""
    chain_tokens: Tuple[str, ...] = ()


@dataclass(frozen=True)
class GenericSourceRecord:
    value: Fraction
    source_unit: str
    record_locator: str
    observed_at: str


@dataclass(frozen=True)
class GenericAdapterSpec:
    source_id: str
    provider: str
    dataset_id: str
    dataset_version: str
    retrieved_at: str
    raw_file: str
    raw_sha256: str
    citation: str
    license_or_terms_ref: str
    access_class: str

    variable_id: str
    source_layer: str
    source_quantity_kind: str
    source_status: str

    target_node_id: str
    target_node_class: str
    spatial_method: str
    spatial_method_ref: str

    interval_id: str
    temporal_method: str
    temporal_method_ref: str

    as_of: str
    max_age_seconds: int

    uncertainty_kind: str
    uncertainty_method_ref: str

    missingness_reason: str
    source_gas_basis: str
    sign_semantics_declared: bool

    base_transform_chain: Tuple[str, ...]
    pre_contract_transform: PreContractTransform = PreContractTransform()


class GenericAdapterContractError(AssertionError):
    pass


def _verify_frozen_raw(spec: GenericAdapterSpec) -> None:
    p = Path(spec.raw_file)
    raw = p.read_bytes()
    got = hashlib.sha256(raw).hexdigest()
    if got != spec.raw_sha256:
        raise GenericAdapterContractError(
            f"raw SHA256 mismatch actual={got} expected={spec.raw_sha256}"
        )


def _apply_pre_contract_transform(
    spec: GenericAdapterSpec,
    record: GenericSourceRecord,
) -> tuple[Fraction, str, str, Tuple[str, ...]]:
    t = spec.pre_contract_transform
    if not t.enabled:
        return record.value, record.source_unit, spec.source_gas_basis, ()

    if not t.from_unit or not t.to_unit:
        raise GenericAdapterContractError("enabled pre-contract transform requires units")
    if record.source_unit != t.from_unit:
        raise GenericAdapterContractError(
            f"pre-contract source unit mismatch {record.source_unit!r} != {t.from_unit!r}"
        )
    if t.factor_d == 0:
        raise GenericAdapterContractError("pre-contract transform denominator cannot be zero")
    if not t.evidence_ref:
        raise GenericAdapterContractError("pre-contract transform requires evidence_ref")

    value = record.value * Fraction(t.factor_n, t.factor_d)
    gas_basis = t.to_gas_basis or spec.source_gas_basis
    return value, t.to_unit, gas_basis, tuple(t.chain_tokens)


def adapt(
    spec: GenericAdapterSpec,
    record: GenericSourceRecord,
) -> admission.AdmissionReceipt:
    """Route one frozen provider record through the shared empirical admission boundary.

    This function performs no balance, storage, process-coupling, stress, score,
    or provider-specific physics calculation. It only verifies the frozen raw
    snapshot, applies an explicitly declared pre-contract unit/basis transform,
    constructs the provider-neutral empirical candidate, and invokes the
    unchanged admission validator.
    """
    _verify_frozen_raw(spec)
    value, source_unit, gas_basis, pre_chain = _apply_pre_contract_transform(spec, record)

    provenance = admission.ProvenanceRecord(
        source_id=spec.source_id,
        provider=spec.provider,
        dataset_id=spec.dataset_id,
        dataset_version=spec.dataset_version,
        record_locator=record.record_locator,
        observed_at=record.observed_at,
        retrieved_at=spec.retrieved_at,
        raw_sha256=spec.raw_sha256,
        citation=spec.citation,
        license_or_terms_ref=spec.license_or_terms_ref,
        access_class=spec.access_class,
    )

    spatial = admission.SpatialMapping(
        method=admission.SpatialMethod(spec.spatial_method),
        target_node_id=spec.target_node_id,
        target_node_class=spec.target_node_class,
        method_ref=spec.spatial_method_ref,
    )

    temporal = admission.TemporalAlignment(
        method=admission.TemporalMethod(spec.temporal_method),
        source_interval_id=spec.interval_id,
        target_interval_id=spec.interval_id,
        method_ref=spec.temporal_method_ref,
        interpolation_used=False,
        interpolation_method_ref="",
        imputation_used=False,
        imputation_method_ref="",
    )

    uncertainty = admission.UncertaintyDeclaration(
        kind=admission.UncertaintyKind(spec.uncertainty_kind),
        method_ref=spec.uncertainty_method_ref,
    )

    candidate = admission.EmpiricalCandidate(
        variable_id=spec.variable_id,
        value=value,
        source_unit=source_unit,
        source_layer=spec.source_layer,
        source_quantity_kind=spec.source_quantity_kind,
        source_status=admission.SourceStatus(spec.source_status),
        provenance=provenance,
        spatial_mapping=spatial,
        temporal_alignment=temporal,
        uncertainty=uncertainty,
        as_of=spec.as_of,
        max_age_seconds=int(spec.max_age_seconds),
        missingness_reason=spec.missingness_reason,
        source_gas_basis=gas_basis,
        sign_semantics_declared=bool(spec.sign_semantics_declared),
        transform_chain=tuple(spec.base_transform_chain) + tuple(pre_chain),
    )
    return admission.admit(candidate)
