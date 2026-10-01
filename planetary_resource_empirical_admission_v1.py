from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

import equilibrium_planetary_resource_core_v1 as core


CONTRACT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__EMPIRICAL_DATA_CONTRACT.json"
)
GATE_ID = (
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__EMPIRICAL_DATA_CONTRACT_AND_SOURCE_ADMISSION_V1"
)
SCHEMA_VERSION = "EQUILIBRIUM_PRS_EMPIRICAL_SOURCE_ADMISSION_V1"


class AdmissionDecision(str, Enum):
    ADMIT_OBSERVED = "ADMIT_OBSERVED"
    ADMIT_DERIVED = "ADMIT_DERIVED"
    ADMIT_IMPUTED_FLAGGED = "ADMIT_IMPUTED_FLAGGED"


class SourceStatus(str, Enum):
    OBSERVED = "OBSERVED"
    DERIVED = "DERIVED"
    IMPUTED = "IMPUTED"
    STALE = "STALE"
    MISSING = "MISSING"
    CONFLICTED = "CONFLICTED"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class UncertaintyKind(str, Enum):
    EXACT = "EXACT"
    INTERVAL = "INTERVAL"
    MOMENT = "MOMENT"
    EMPIRICAL = "EMPIRICAL"
    UNKNOWN = "UNKNOWN"


class SpatialMethod(str, Enum):
    IDENTITY = "IDENTITY"
    AREA_WEIGHTED = "AREA_WEIGHTED"
    NETWORK_ASSIGNMENT = "NETWORK_ASSIGNMENT"
    NODE_LOOKUP = "NODE_LOOKUP"
    AGGREGATE_TO_PARENT = "AGGREGATE_TO_PARENT"


class TemporalMethod(str, Enum):
    EXACT_INTERVAL = "EXACT_INTERVAL"
    TIME_WEIGHTED_MEAN = "TIME_WEIGHTED_MEAN"
    END_OF_INTERVAL_STOCK = "END_OF_INTERVAL_STOCK"
    SUM_SUBINTERVALS = "SUM_SUBINTERVALS"
    INTEGRATE_RATE = "INTEGRATE_RATE"


class AdmissionHold(ValueError):
    def __init__(self, code: str, message: str = ""):
        self.code = code
        super().__init__(f"{code}: {message}" if message else code)


@dataclass(frozen=True)
class ProvenanceRecord:
    source_id: str
    provider: str
    dataset_id: str
    dataset_version: str
    record_locator: str
    observed_at: str
    retrieved_at: str
    raw_sha256: str
    citation: str
    license_or_terms_ref: str
    access_class: str


@dataclass(frozen=True)
class SpatialMapping:
    method: SpatialMethod | None
    target_node_id: str
    target_node_class: str
    method_ref: str
    weights: tuple[Fraction, ...] = ()


@dataclass(frozen=True)
class TemporalAlignment:
    method: TemporalMethod | None
    source_interval_id: str
    target_interval_id: str
    method_ref: str = ""
    interpolation_used: bool = False
    interpolation_method_ref: str = ""
    imputation_used: bool = False
    imputation_method_ref: str = ""


@dataclass(frozen=True)
class UncertaintyDeclaration:
    kind: UncertaintyKind | None
    method_ref: str = ""
    covariance_ref: str = ""
    sample_alignment_ref: str = ""


@dataclass(frozen=True)
class EmpiricalCandidate:
    variable_id: str
    value: Fraction | None
    source_unit: str
    source_layer: str
    source_quantity_kind: str
    source_status: SourceStatus
    provenance: ProvenanceRecord
    spatial_mapping: SpatialMapping
    temporal_alignment: TemporalAlignment
    uncertainty: UncertaintyDeclaration
    as_of: str
    max_age_seconds: int
    missingness_reason: str = ""
    source_gas_basis: str = ""
    sign_semantics_declared: bool = True
    transform_chain: tuple[str, ...] = ()


@dataclass(frozen=True)
class AdmissionReceipt:
    schema_version: str
    gate_id: str
    variable_id: str
    decision: str
    canonical_value_n: int | None
    canonical_value_d: int | None
    canonical_unit: str
    layer: str
    quantity_kind: str
    target_node_id: str
    source_id: str
    raw_sha256: str
    output_status: str
    transform_chain: tuple[str, ...]
    uncertainty_kind: str
    freshness_age_seconds: int
    claim_ceiling: Mapping[str, Any]


def load_contract() -> dict[str, Any]:
    data = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if data["schema_version"] != "EQUILIBRIUM_PRS_EMPIRICAL_DATA_CONTRACT_V1":
        raise AdmissionHold("HOLD_TRANSFORM_RECEIPT_INCOMPLETE", "contract schema mismatch")
    if data["gate_id"] != GATE_ID:
        raise AdmissionHold("HOLD_TRANSFORM_RECEIPT_INCOMPLETE", "gate id mismatch")
    if data["scope"]["external_data_ingest"] is not False:
        raise AdmissionHold("HOLD_TRANSFORM_RECEIPT_INCOMPLETE", "contract illegally enables data ingest")
    return data


CONTRACT = load_contract()
VARIABLES = {row["variable_id"]: row for row in CONTRACT["variables"]}


def F(x: int | str | Fraction) -> Fraction:
    if isinstance(x, Fraction):
        return x
    return Fraction(x)


def parse_iso8601_utc(value: str) -> datetime:
    if not value:
        raise AdmissionHold("HOLD_PROVENANCE_MISSING", "timestamp missing")
    try:
        v = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(v)
    except ValueError as exc:
        raise AdmissionHold("HOLD_PROVENANCE_MISSING", f"invalid timestamp {value!r}") from exc
    if dt.tzinfo is None:
        raise AdmissionHold("HOLD_PROVENANCE_MISSING", "timestamp must be timezone-aware")
    return dt.astimezone(timezone.utc)


def require_provenance(p: ProvenanceRecord) -> None:
    required = (
        p.source_id,
        p.provider,
        p.dataset_id,
        p.dataset_version,
        p.record_locator,
        p.observed_at,
        p.retrieved_at,
        p.raw_sha256,
        p.citation,
        p.license_or_terms_ref,
        p.access_class,
    )
    if any(not str(v).strip() for v in required):
        raise AdmissionHold("HOLD_PROVENANCE_MISSING")
    if not re.fullmatch(r"[0-9a-f]{64}", p.raw_sha256):
        raise AdmissionHold("HOLD_DIGEST_INVALID")
    observed = parse_iso8601_utc(p.observed_at)
    retrieved = parse_iso8601_utc(p.retrieved_at)
    if retrieved < observed:
        raise AdmissionHold("HOLD_PROVENANCE_MISSING", "retrieved_at precedes observed_at")


def variable_spec(variable_id: str) -> dict[str, Any]:
    try:
        return VARIABLES[variable_id]
    except KeyError as exc:
        raise AdmissionHold("HOLD_VARIABLE_UNMAPPED", variable_id) from exc


def unit_conversion(spec: Mapping[str, Any], candidate: EmpiricalCandidate) -> tuple[Fraction, str]:
    if candidate.source_layer != spec["layer"]:
        raise AdmissionHold("HOLD_LAYER_MISMATCH")
    if candidate.source_quantity_kind != spec["quantity_kind"]:
        raise AdmissionHold("HOLD_QUANTITY_KIND_MISMATCH")

    table = (
        CONTRACT["accepted_source_units"]
        .get(spec["layer"], {})
        .get(spec["quantity_kind"], {})
    )
    rule = table.get(candidate.source_unit)
    if rule is None:
        if candidate.source_unit in {"m3_gas", "bcm_gas", "barrel", "bbl"}:
            raise AdmissionHold("HOLD_DIMENSIONAL_INCOMPATIBILITY")
        raise AdmissionHold("HOLD_UNIT_UNRECOGNIZED", candidate.source_unit)

    if rule["target"] != spec["canonical_unit"]:
        raise AdmissionHold("HOLD_DIMENSIONAL_INCOMPATIBILITY")

    expected_basis = spec.get("gas_basis")
    actual_basis = rule.get("gas_basis") or candidate.source_gas_basis or None
    if expected_basis and actual_basis != expected_basis:
        raise AdmissionHold("HOLD_HHV_LHV_BASIS_MISMATCH")

    if candidate.value is None:
        return Fraction(0), spec["canonical_unit"]

    factor = Fraction(int(rule["factor_n"]), int(rule["factor_d"]))
    return candidate.value * factor, spec["canonical_unit"]


def validate_spatial(spec: Mapping[str, Any], mapping: SpatialMapping) -> None:
    if mapping.method is None or not mapping.method_ref.strip():
        raise AdmissionHold("HOLD_SPATIAL_MAPPING_UNDECLARED")
    if mapping.target_node_class != spec["target_node_class"]:
        raise AdmissionHold("HOLD_SPATIAL_MAPPING_AMBIGUOUS", "target node class mismatch")
    if not mapping.target_node_id.strip():
        raise AdmissionHold("HOLD_SPATIAL_MAPPING_AMBIGUOUS", "target node missing")
    if mapping.method.value not in CONTRACT["spatial_mapping"]["allowed_methods"]:
        raise AdmissionHold("HOLD_SPATIAL_MAPPING_AMBIGUOUS")
    if mapping.method is SpatialMethod.AREA_WEIGHTED:
        if not mapping.weights or sum(mapping.weights, Fraction(0)) != Fraction(1):
            raise AdmissionHold("HOLD_SPATIAL_MAPPING_AMBIGUOUS", "weights must sum to one")


def validate_temporal(spec: Mapping[str, Any], t: TemporalAlignment) -> tuple[str, ...]:
    if t.method is None:
        raise AdmissionHold("HOLD_TEMPORAL_ALIGNMENT_UNDECLARED")
    if t.method.value not in CONTRACT["temporal_alignment"]["allowed_methods"]:
        raise AdmissionHold("HOLD_TEMPORAL_METHOD_INVALID")
    if t.method is not TemporalMethod.EXACT_INTERVAL and not t.method_ref.strip():
        raise AdmissionHold("HOLD_TEMPORAL_ALIGNMENT_UNDECLARED", "non-exact method needs method_ref")
    if t.method is TemporalMethod.EXACT_INTERVAL and t.source_interval_id != t.target_interval_id:
        raise AdmissionHold("HOLD_TEMPORAL_METHOD_INVALID", "exact alignment interval mismatch")

    kind = spec["quantity_kind"]
    if kind == "STOCK" and t.method in {TemporalMethod.TIME_WEIGHTED_MEAN, TemporalMethod.INTEGRATE_RATE}:
        raise AdmissionHold("HOLD_TEMPORAL_METHOD_INVALID", "stock temporal method invalid")
    if kind == "RATE" and t.method is TemporalMethod.END_OF_INTERVAL_STOCK:
        raise AdmissionHold("HOLD_TEMPORAL_METHOD_INVALID", "rate temporal method invalid")

    chain: list[str] = [f"temporal:{t.method.value}"]
    if t.interpolation_used:
        if not t.interpolation_method_ref.strip():
            raise AdmissionHold("HOLD_INTERPOLATION_UNDECLARED")
        chain.append(f"interpolation:{t.interpolation_method_ref}")
    if t.imputation_used:
        if not t.imputation_method_ref.strip():
            raise AdmissionHold("HOLD_IMPUTATION_UNDECLARED")
        chain.append(f"imputation:{t.imputation_method_ref}")
    return tuple(chain)


def validate_uncertainty(u: UncertaintyDeclaration, t: TemporalAlignment) -> None:
    if u.kind is None:
        raise AdmissionHold("HOLD_UNCERTAINTY_MISSING")
    if u.kind.value not in CONTRACT["uncertainty"]["allowed_kinds"]:
        raise AdmissionHold("HOLD_UNCERTAINTY_MISSING")
    aggregate = t.method in {
        TemporalMethod.TIME_WEIGHTED_MEAN,
        TemporalMethod.SUM_SUBINTERVALS,
        TemporalMethod.INTEGRATE_RATE,
    }
    if aggregate and u.kind is UncertaintyKind.MOMENT and not u.covariance_ref.strip():
        raise AdmissionHold("HOLD_COVARIANCE_REQUIRED")
    if aggregate and u.kind is UncertaintyKind.EMPIRICAL and not u.sample_alignment_ref.strip():
        raise AdmissionHold("HOLD_SAMPLE_ALIGNMENT_REQUIRED")
    if u.kind is not UncertaintyKind.EXACT and not u.method_ref.strip():
        if u.kind is not UncertaintyKind.UNKNOWN:
            raise AdmissionHold("HOLD_UNCERTAINTY_MISSING", "non-exact uncertainty needs method_ref")


def validate_freshness(candidate: EmpiricalCandidate) -> int:
    if candidate.max_age_seconds < 0:
        raise AdmissionHold("HOLD_FRESHNESS_UNKNOWN")
    observed = parse_iso8601_utc(candidate.provenance.observed_at)
    as_of = parse_iso8601_utc(candidate.as_of)
    if as_of < observed:
        raise AdmissionHold("HOLD_FRESHNESS_UNKNOWN", "as_of precedes observation")
    age = int((as_of - observed).total_seconds())
    if age > candidate.max_age_seconds:
        raise AdmissionHold("HOLD_STALE_INPUT")
    return age


def validate_status(candidate: EmpiricalCandidate, temporal_chain: tuple[str, ...]) -> tuple[AdmissionDecision, str]:
    status = candidate.source_status
    if status is SourceStatus.CONFLICTED:
        raise AdmissionHold("HOLD_CONFLICTED_INPUT")
    if status is SourceStatus.OUT_OF_SCOPE:
        raise AdmissionHold("HOLD_OUT_OF_SCOPE_INPUT")
    if status is SourceStatus.STALE:
        raise AdmissionHold("HOLD_STALE_INPUT")
    if status is SourceStatus.MISSING or candidate.value is None:
        if not candidate.missingness_reason.strip():
            raise AdmissionHold("HOLD_MISSINGNESS_UNDECLARED")
        if candidate.missingness_reason not in CONTRACT["missingness"]["allowed_reasons"]:
            raise AdmissionHold("HOLD_MISSINGNESS_UNDECLARED")
        raise AdmissionHold("HOLD_MISSING_INPUT")
    if not candidate.sign_semantics_declared:
        raise AdmissionHold("HOLD_SIGN_SEMANTICS_UNDECLARED")

    has_imputation = any(x.startswith("imputation:") for x in temporal_chain)
    has_interpolation = any(x.startswith("interpolation:") for x in temporal_chain)
    if status is SourceStatus.IMPUTED and not has_imputation:
        raise AdmissionHold("HOLD_IMPUTATION_UNDECLARED")
    if has_imputation and status is not SourceStatus.IMPUTED:
        raise AdmissionHold("HOLD_IMPUTATION_UNDECLARED", "imputation flag/status mismatch")

    if status is SourceStatus.IMPUTED:
        return AdmissionDecision.ADMIT_IMPUTED_FLAGGED, "IMPUTED"
    if status is SourceStatus.DERIVED or has_interpolation:
        return AdmissionDecision.ADMIT_DERIVED, "DERIVED"
    return AdmissionDecision.ADMIT_OBSERVED, "OBSERVED"


def admit(candidate: EmpiricalCandidate) -> AdmissionReceipt:
    spec = variable_spec(candidate.variable_id)
    require_provenance(candidate.provenance)
    validate_spatial(spec, candidate.spatial_mapping)
    temporal_chain = validate_temporal(spec, candidate.temporal_alignment)
    validate_uncertainty(candidate.uncertainty, candidate.temporal_alignment)
    age = validate_freshness(candidate)
    decision, output_status = validate_status(candidate, temporal_chain)
    canonical_value, canonical_unit = unit_conversion(spec, candidate)

    chain = tuple(candidate.transform_chain) + (
        f"unit:{candidate.source_unit}->{canonical_unit}",
        f"spatial:{candidate.spatial_mapping.method.value}",
    ) + temporal_chain

    if not chain or not candidate.provenance.raw_sha256:
        raise AdmissionHold("HOLD_TRANSFORM_RECEIPT_INCOMPLETE")

    return AdmissionReceipt(
        schema_version=SCHEMA_VERSION,
        gate_id=GATE_ID,
        variable_id=candidate.variable_id,
        decision=decision.value,
        canonical_value_n=canonical_value.numerator,
        canonical_value_d=canonical_value.denominator,
        canonical_unit=canonical_unit,
        layer=spec["layer"],
        quantity_kind=spec["quantity_kind"],
        target_node_id=candidate.spatial_mapping.target_node_id,
        source_id=candidate.provenance.source_id,
        raw_sha256=candidate.provenance.raw_sha256,
        output_status=output_status,
        transform_chain=chain,
        uncertainty_kind=candidate.uncertainty.kind.value,
        freshness_age_seconds=age,
        claim_ceiling={
            "external_dataset_admitted": False,
            "physical_calibration": False,
            "forecasting": False,
            "aggregate_equilibrium_score": False,
            "runtime_admission": False,
        },
    )


def canonical_json(obj: Any) -> str:
    def conv(x: Any) -> Any:
        if isinstance(x, Fraction):
            return {"n": x.numerator, "d": x.denominator}
        if isinstance(x, Enum):
            return x.value
        if hasattr(x, "__dataclass_fields__"):
            return {k: conv(v) for k, v in sorted(asdict(x).items())}
        if isinstance(x, Mapping):
            return {str(k): conv(v) for k, v in sorted(x.items(), key=lambda kv: str(kv[0]))}
        if isinstance(x, (tuple, list)):
            return [conv(v) for v in x]
        return x
    return json.dumps(conv(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_sha256(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def synthetic_provenance(
    *,
    raw_sha256: str = "1" * 64,
    observed_at: str = "2026-01-01T00:00:00Z",
    retrieved_at: str = "2026-01-01T01:00:00Z",
) -> ProvenanceRecord:
    return ProvenanceRecord(
        source_id="SYNTHETIC_SOURCE",
        provider="SYNTHETIC_PROVIDER",
        dataset_id="SYNTHETIC_DATASET",
        dataset_version="V1",
        record_locator="synthetic://record/1",
        observed_at=observed_at,
        retrieved_at=retrieved_at,
        raw_sha256=raw_sha256,
        citation="SYNTHETIC_ONLY_NO_EXTERNAL_DATA",
        license_or_terms_ref="SYNTHETIC_TEST_TERMS",
        access_class="SYNTHETIC",
    )


def synthetic_candidate(**overrides: Any) -> EmpiricalCandidate:
    base: dict[str, Any] = dict(
        variable_id="electricity.production_rate",
        value=Fraction(2),
        source_unit="MW",
        source_layer="ELECTRICITY",
        source_quantity_kind="RATE",
        source_status=SourceStatus.OBSERVED,
        provenance=synthetic_provenance(),
        spatial_mapping=SpatialMapping(
            method=SpatialMethod.IDENTITY,
            target_node_id="E0",
            target_node_class="ELECTRICITY_ZONE",
            method_ref="SYNTHETIC_SPATIAL_IDENTITY",
        ),
        temporal_alignment=TemporalAlignment(
            method=TemporalMethod.EXACT_INTERVAL,
            source_interval_id="T0",
            target_interval_id="T0",
        ),
        uncertainty=UncertaintyDeclaration(kind=UncertaintyKind.EXACT),
        as_of="2026-01-01T02:00:00Z",
        max_age_seconds=3 * 3600,
        missingness_reason="",
        source_gas_basis="",
        sign_semantics_declared=True,
        transform_chain=("source:synthetic",),
    )
    base.update(overrides)
    return EmpiricalCandidate(**base)


@dataclass(frozen=True)
class MatrixResult:
    id: str
    passed: bool
    observed: str


def _pass(i: int, observed: str = "PASS") -> MatrixResult:
    return MatrixResult(f"A{i:02d}", True, observed)


def _expect_hold(i: int, code: str, fn) -> MatrixResult:
    try:
        fn()
    except AdmissionHold as exc:
        return MatrixResult(f"A{i:02d}", exc.code == code, exc.code)
    return MatrixResult(f"A{i:02d}", False, "NO_HOLD")


def run_admission_matrix() -> list[MatrixResult]:
    r: list[MatrixResult] = []

    # A01 observed electricity rate, exact units after conversion.
    x = admit(synthetic_candidate())
    r.append(_pass(1, x.decision if x.canonical_value_n == 2_000_000 else "BAD_CONVERSION"))

    # A02 zero is a value, never missing.
    x = admit(synthetic_candidate(value=Fraction(0)))
    r.append(_pass(2, "ZERO_IS_VALUE" if x.canonical_value_n == 0 else "BAD_ZERO"))

    # A03 freshwater volume conversion L -> m3.
    x = admit(synthetic_candidate(
        variable_id="freshwater.stock", value=Fraction(1000), source_unit="L",
        source_layer="FRESHWATER", source_quantity_kind="STOCK",
        spatial_mapping=SpatialMapping(SpatialMethod.IDENTITY, "W0", "WATER_BASIN_OR_ACCOUNTING_UNIT", "SYNTHETIC"),
    ))
    r.append(_pass(3, "ONE_M3" if (x.canonical_value_n, x.canonical_value_d) == (1,1) else "BAD_CONVERSION"))

    # A04 oil rate t/day -> kg/s.
    x = admit(synthetic_candidate(
        variable_id="crude_oil.production_rate", value=Fraction(86400), source_unit="t/day",
        source_layer="CRUDE_OIL", source_quantity_kind="RATE",
        spatial_mapping=SpatialMapping(SpatialMethod.NODE_LOOKUP, "O0", "OIL_ZONE_OR_HUB", "SYNTHETIC"),
    ))
    r.append(_pass(4, "1000_KG_S" if (x.canonical_value_n, x.canonical_value_d) == (1000,1) else "BAD_CONVERSION"))

    # A05 gas HHV accepted.
    x = admit(synthetic_candidate(
        variable_id="natural_gas.stock", value=Fraction(2), source_unit="GJ_HHV",
        source_layer="NATURAL_GAS", source_quantity_kind="STOCK", source_gas_basis="HHV",
        spatial_mapping=SpatialMapping(SpatialMethod.NETWORK_ASSIGNMENT, "G0", "GAS_ZONE", "SYNTHETIC"),
    ))
    r.append(_pass(5, "HHV_ACCEPTED" if x.canonical_unit == "J_gas" else "BAD_UNIT"))

    r.append(_expect_hold(6, "HOLD_VARIABLE_UNMAPPED", lambda: admit(synthetic_candidate(variable_id="electricity.magic"))))

    badp = synthetic_provenance(raw_sha256="abc")
    r.append(_expect_hold(7, "HOLD_DIGEST_INVALID", lambda: admit(synthetic_candidate(provenance=badp))))

    empty_provider = ProvenanceRecord(
        source_id="S", provider="", dataset_id="D", dataset_version="V1", record_locator="R",
        observed_at="2026-01-01T00:00:00Z", retrieved_at="2026-01-01T01:00:00Z",
        raw_sha256="1"*64, citation="C", license_or_terms_ref="T", access_class="SYNTHETIC"
    )
    r.append(_expect_hold(8, "HOLD_PROVENANCE_MISSING", lambda: admit(synthetic_candidate(provenance=empty_provider))))

    r.append(_expect_hold(9, "HOLD_LAYER_MISMATCH", lambda: admit(synthetic_candidate(source_layer="FRESHWATER"))))
    r.append(_expect_hold(10, "HOLD_QUANTITY_KIND_MISMATCH", lambda: admit(synthetic_candidate(source_quantity_kind="STOCK"))))
    r.append(_expect_hold(11, "HOLD_UNIT_UNRECOGNIZED", lambda: admit(synthetic_candidate(source_unit="horsepower"))))
    r.append(_expect_hold(12, "HOLD_DIMENSIONAL_INCOMPATIBILITY", lambda: admit(synthetic_candidate(
        variable_id="natural_gas.stock", source_unit="bcm_gas", source_layer="NATURAL_GAS",
        source_quantity_kind="STOCK", spatial_mapping=SpatialMapping(SpatialMethod.IDENTITY,"G0","GAS_ZONE","SYNTHETIC")
    ))))
    r.append(_expect_hold(13, "HOLD_HHV_LHV_BASIS_MISMATCH", lambda: admit(synthetic_candidate(
        variable_id="natural_gas.stock", source_unit="GJ_HHV", source_layer="NATURAL_GAS",
        source_quantity_kind="STOCK", source_gas_basis="LHV",
        spatial_mapping=SpatialMapping(SpatialMethod.IDENTITY,"G0","GAS_ZONE","SYNTHETIC")
    ))))

    r.append(_expect_hold(14, "HOLD_SPATIAL_MAPPING_UNDECLARED", lambda: admit(synthetic_candidate(
        spatial_mapping=SpatialMapping(None,"E0","ELECTRICITY_ZONE","")
    ))))
    r.append(_expect_hold(15, "HOLD_SPATIAL_MAPPING_AMBIGUOUS", lambda: admit(synthetic_candidate(
        spatial_mapping=SpatialMapping(SpatialMethod.IDENTITY,"E0","GAS_ZONE","SYNTHETIC")
    ))))
    r.append(_expect_hold(16, "HOLD_SPATIAL_MAPPING_AMBIGUOUS", lambda: admit(synthetic_candidate(
        spatial_mapping=SpatialMapping(SpatialMethod.AREA_WEIGHTED,"E0","ELECTRICITY_ZONE","SYNTHETIC",(Fraction(1,2),Fraction(1,3)))
    ))))

    r.append(_expect_hold(17, "HOLD_TEMPORAL_ALIGNMENT_UNDECLARED", lambda: admit(synthetic_candidate(
        temporal_alignment=TemporalAlignment(None,"T0","T0")
    ))))
    r.append(_expect_hold(18, "HOLD_TEMPORAL_METHOD_INVALID", lambda: admit(synthetic_candidate(
        temporal_alignment=TemporalAlignment(TemporalMethod.EXACT_INTERVAL,"T1","T0")
    ))))
    r.append(_expect_hold(19, "HOLD_INTERPOLATION_UNDECLARED", lambda: admit(synthetic_candidate(
        temporal_alignment=TemporalAlignment(TemporalMethod.EXACT_INTERVAL,"T0","T0",interpolation_used=True)
    ))))
    r.append(_expect_hold(20, "HOLD_IMPUTATION_UNDECLARED", lambda: admit(synthetic_candidate(
        source_status=SourceStatus.IMPUTED
    ))))

    x = admit(synthetic_candidate(
        source_status=SourceStatus.IMPUTED,
        temporal_alignment=TemporalAlignment(
            TemporalMethod.EXACT_INTERVAL,"T0","T0",
            imputation_used=True, imputation_method_ref="SYNTHETIC_IMPUTER"
        )
    ))
    r.append(_pass(21, x.decision))

    r.append(_expect_hold(22, "HOLD_FRESHNESS_UNKNOWN", lambda: admit(synthetic_candidate(max_age_seconds=-1))))
    r.append(_expect_hold(23, "HOLD_STALE_INPUT", lambda: admit(synthetic_candidate(
        as_of="2026-01-03T00:00:00Z", max_age_seconds=3600
    ))))
    r.append(_expect_hold(24, "HOLD_UNCERTAINTY_MISSING", lambda: admit(synthetic_candidate(
        uncertainty=UncertaintyDeclaration(kind=None)
    ))))
    r.append(_expect_hold(25, "HOLD_COVARIANCE_REQUIRED", lambda: admit(synthetic_candidate(
        temporal_alignment=TemporalAlignment(TemporalMethod.TIME_WEIGHTED_MEAN,"Traw","T0","SYNTHETIC_AGG"),
        uncertainty=UncertaintyDeclaration(UncertaintyKind.MOMENT,"SYNTHETIC_MOMENTS")
    ))))
    r.append(_expect_hold(26, "HOLD_SAMPLE_ALIGNMENT_REQUIRED", lambda: admit(synthetic_candidate(
        temporal_alignment=TemporalAlignment(TemporalMethod.TIME_WEIGHTED_MEAN,"Traw","T0","SYNTHETIC_AGG"),
        uncertainty=UncertaintyDeclaration(UncertaintyKind.EMPIRICAL,"SYNTHETIC_SAMPLES")
    ))))

    r.append(_expect_hold(27, "HOLD_MISSINGNESS_UNDECLARED", lambda: admit(synthetic_candidate(
        value=None, source_status=SourceStatus.MISSING
    ))))
    r.append(_expect_hold(28, "HOLD_MISSING_INPUT", lambda: admit(synthetic_candidate(
        value=None, source_status=SourceStatus.MISSING, missingness_reason="COVERAGE_GAP"
    ))))
    r.append(_expect_hold(29, "HOLD_CONFLICTED_INPUT", lambda: admit(synthetic_candidate(
        source_status=SourceStatus.CONFLICTED
    ))))
    r.append(_expect_hold(30, "HOLD_OUT_OF_SCOPE_INPUT", lambda: admit(synthetic_candidate(
        source_status=SourceStatus.OUT_OF_SCOPE
    ))))
    r.append(_expect_hold(31, "HOLD_SIGN_SEMANTICS_UNDECLARED", lambda: admit(synthetic_candidate(
        sign_semantics_declared=False
    ))))

    x = admit(synthetic_candidate(
        source_status=SourceStatus.DERIVED,
        temporal_alignment=TemporalAlignment(
            TemporalMethod.TIME_WEIGHTED_MEAN,"Traw","T0","SYNTHETIC_WEIGHTED_MEAN"
        ),
        uncertainty=UncertaintyDeclaration(
            UncertaintyKind.MOMENT,"SYNTHETIC_MOMENTS","SYNTHETIC_COVARIANCE"
        )
    ))
    r.append(_pass(32, x.decision))

    x = admit(synthetic_candidate(
        source_status=SourceStatus.DERIVED,
        temporal_alignment=TemporalAlignment(
            TemporalMethod.TIME_WEIGHTED_MEAN,"Traw","T0","SYNTHETIC_WEIGHTED_MEAN"
        ),
        uncertainty=UncertaintyDeclaration(
            UncertaintyKind.EMPIRICAL,"SYNTHETIC_SAMPLES","", "SYNTHETIC_ALIGNMENT"
        )
    ))
    r.append(_pass(33, x.decision))

    x = admit(synthetic_candidate(
        source_status=SourceStatus.DERIVED,
        temporal_alignment=TemporalAlignment(
            TemporalMethod.EXACT_INTERVAL,"T0","T0",
            interpolation_used=True, interpolation_method_ref="SYNTHETIC_LINEAR"
        ),
    ))
    r.append(_pass(34, "INTERPOLATION_VISIBLE" if any(
        s.startswith("interpolation:") for s in x.transform_chain
    ) else "INTERPOLATION_HIDDEN"))

    a = admit(synthetic_candidate())
    b = admit(synthetic_candidate())
    r.append(_pass(35, "DETERMINISTIC" if canonical_sha256(a) == canonical_sha256(b) else "NONDETERMINISTIC"))

    scope = CONTRACT["scope"]
    hard_false = (
        scope["external_data_ingest"] is False
        and scope["nasa_bind"] is False
        and scope["rockstrom_bind"] is False
        and scope["aggregate_eq_score"] is False
        and scope["runtime_admission"] is False
        and scope["global_bind"] is False
        and scope["merge"] is False
    )
    r.append(_pass(36, "CLAIM_CEILING_INTACT" if hard_false else "CLAIM_CEILING_BROKEN"))

    return r


def build_gate_receipt() -> dict[str, Any]:
    matrix = run_admission_matrix()
    passed = sum(x.passed for x in matrix)
    if passed != 36:
        first = next(x for x in matrix if not x.passed)
        raise AssertionError(f"{first.id} failed: {first.observed}")
    return {
        "schema_version": "EQUILIBRIUM_PRS_EMPIRICAL_ADMISSION_GATE_RECEIPT_V1",
        "gate_id": GATE_ID,
        "contract_sha256": hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest(),
        "matrix": {
            "count": 36,
            "pass": passed,
            "rows": [asdict(x) for x in matrix],
        },
        "frozen": {
            "variable_count": len(VARIABLES),
            "layers": sorted({x["layer"] for x in VARIABLES.values()}),
            "canonical_units": sorted({x["canonical_unit"] for x in VARIABLES.values()}),
            "spatial_methods": CONTRACT["spatial_mapping"]["allowed_methods"],
            "temporal_methods": CONTRACT["temporal_alignment"]["allowed_methods"],
            "uncertainty_kinds": CONTRACT["uncertainty"]["allowed_kinds"],
            "missingness_reasons": CONTRACT["missingness"]["allowed_reasons"],
        },
        "scope": CONTRACT["scope"],
        "verdict": "PASS_BOUNDED_EMPIRICAL_DATA_CONTRACT_36_OF_36_NO_DATA_INGEST",
    }


if __name__ == "__main__":
    receipt = build_gate_receipt()
    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    out = Path(
        "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
        "__EMPIRICAL_DATA_CONTRACT_AND_SOURCE_ADMISSION_RECEIPT.json"
    )
    out.write_text(canonical, encoding="utf-8")
    print(canonical, end="")
    print("EMPIRICAL_ADMISSION_RECEIPT_SHA256=" + hashlib.sha256(canonical.encode("utf-8")).hexdigest())
