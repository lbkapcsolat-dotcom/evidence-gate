from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence

GATE_ID = "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1__HGRAPH_REFERENCE_IMPLEMENTATION_AND_40_OF_40_EXECUTABLE_VALIDATION_V1"
CONTRACT_VERSION = "PRS_CORE_V1_REF_1"
HGRAPH_NATIVE_AVAILABLE = False


class ResourceLayer(str, Enum):
    ELECTRICITY = "ELECTRICITY"
    NATURAL_GAS = "NATURAL_GAS"
    CRUDE_OIL = "CRUDE_OIL"
    FRESHWATER = "FRESHWATER"


class QuantityKind(str, Enum):
    STOCK = "STOCK"
    RATE = "RATE"
    DIMENSIONLESS = "DIMENSIONLESS_PARAMETER"
    TIME_INTERVAL = "TIME_INTERVAL"


class EpistemicStatus(str, Enum):
    OBSERVED = "OBSERVED"
    DERIVED = "DERIVED"
    IMPUTED = "IMPUTED"
    STALE = "STALE"
    MISSING = "MISSING"
    CONFLICTED = "CONFLICTED"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class ValueSpace(str, Enum):
    PHYSICAL = "PHYSICAL"
    AUDIT = "AUDIT"
    EVIDENCE = "EVIDENCE_CONFIDENCE"
    STRESS = "STRESS"


class UncertaintyKind(str, Enum):
    EXACT = "EXACT"
    INTERVAL = "INTERVAL"
    MOMENT = "MOMENT"
    EMPIRICAL = "EMPIRICAL"
    UNKNOWN = "UNKNOWN"


class GuardPolicy(str, Enum):
    STRICT_CURRENT_OBSERVED_OR_DERIVED = "STRICT_CURRENT_OBSERVED_OR_DERIVED"
    ALLOW_IMPUTED_WITH_FLAG = "ALLOW_IMPUTED_WITH_FLAG"
    ALLOW_STALE_WITH_MAX_AGE = "ALLOW_STALE_WITH_MAX_AGE"


class HoldCode(str, Enum):
    HOLD_UNIT_MISMATCH = "HOLD_UNIT_MISMATCH"
    HOLD_HHV_LHV_BASIS_MISMATCH = "HOLD_HHV_LHV_BASIS_MISMATCH"
    HOLD_TIME_BASIS_MISMATCH = "HOLD_TIME_BASIS_MISMATCH"
    HOLD_MANIFEST_MISMATCH = "HOLD_MANIFEST_MISMATCH"
    HOLD_TOPOLOGY_CHANGED = "HOLD_TOPOLOGY_CHANGED"
    HOLD_MISSING_INPUT = "HOLD_MISSING_INPUT"
    HOLD_CONFLICTED_INPUT = "HOLD_CONFLICTED_INPUT"
    HOLD_OUT_OF_SCOPE_INPUT = "HOLD_OUT_OF_SCOPE_INPUT"
    HOLD_STALE_INPUT = "HOLD_STALE_INPUT"
    HOLD_IMPUTED_INPUT = "HOLD_IMPUTED_INPUT"
    HOLD_IMPUTED_FLAG_ERASED = "HOLD_IMPUTED_FLAG_ERASED"
    HOLD_DOUBLE_COUNT_LOSS = "HOLD_DOUBLE_COUNT_LOSS"
    HOLD_PROCESS_EVIDENCE = "HOLD_PROCESS_EVIDENCE"
    HOLD_PROCESS_UNIT = "HOLD_PROCESS_UNIT"
    HOLD_PROCESS_SCOPE = "HOLD_PROCESS_SCOPE"
    HOLD_CAUSALITY = "HOLD_CAUSALITY"
    HOLD_STORAGE_CAPACITY = "HOLD_STORAGE_CAPACITY"
    HOLD_STORAGE_RATE = "HOLD_STORAGE_RATE"
    HOLD_EFFICIENCY_DOMAIN = "HOLD_EFFICIENCY_DOMAIN"
    HOLD_UNCERTAINTY_OPERATOR = "HOLD_UNCERTAINTY_OPERATOR"
    HOLD_COVARIANCE_REQUIRED = "HOLD_COVARIANCE_REQUIRED"
    HOLD_SAMPLE_ALIGNMENT_REQUIRED = "HOLD_SAMPLE_ALIGNMENT_REQUIRED"
    HOLD_BOUNDARY_DIRECTION = "HOLD_BOUNDARY_DIRECTION"
    HOLD_NEGATIVE_DIRECTED_FLOW = "HOLD_NEGATIVE_DIRECTED_FLOW"
    HOLD_AUDIT_PHYSICAL_MIX = "HOLD_AUDIT_PHYSICAL_MIX"
    HOLD_STRESS_PHYSICAL_MIX = "HOLD_STRESS_PHYSICAL_MIX"
    HOLD_AGGREGATE_SCORE_PROHIBITED = "HOLD_AGGREGATE_SCORE_PROHIBITED"


class HoldError(ValueError):
    def __init__(self, code: HoldCode, message: str = ""):
        self.code = code
        super().__init__(f"{code.value}: {message}" if message else code.value)


def F(x: int | float | str | Fraction) -> Fraction:
    if isinstance(x, Fraction):
        return x
    if isinstance(x, float):
        return Fraction(str(x))
    return Fraction(x)


@dataclass(frozen=True)
class UnitTag:
    layer: ResourceLayer
    kind: QuantityKind
    symbol: str
    gas_basis: str | None = None


CANONICAL_UNITS: dict[tuple[ResourceLayer, QuantityKind], UnitTag] = {
    (ResourceLayer.ELECTRICITY, QuantityKind.STOCK): UnitTag(ResourceLayer.ELECTRICITY, QuantityKind.STOCK, "J_e"),
    (ResourceLayer.ELECTRICITY, QuantityKind.RATE): UnitTag(ResourceLayer.ELECTRICITY, QuantityKind.RATE, "W_e"),
    (ResourceLayer.NATURAL_GAS, QuantityKind.STOCK): UnitTag(ResourceLayer.NATURAL_GAS, QuantityKind.STOCK, "J_gas", "HHV"),
    (ResourceLayer.NATURAL_GAS, QuantityKind.RATE): UnitTag(ResourceLayer.NATURAL_GAS, QuantityKind.RATE, "W_th", "HHV"),
    (ResourceLayer.CRUDE_OIL, QuantityKind.STOCK): UnitTag(ResourceLayer.CRUDE_OIL, QuantityKind.STOCK, "kg_crude"),
    (ResourceLayer.CRUDE_OIL, QuantityKind.RATE): UnitTag(ResourceLayer.CRUDE_OIL, QuantityKind.RATE, "kg/s"),
    (ResourceLayer.FRESHWATER, QuantityKind.STOCK): UnitTag(ResourceLayer.FRESHWATER, QuantityKind.STOCK, "m3"),
    (ResourceLayer.FRESHWATER, QuantityKind.RATE): UnitTag(ResourceLayer.FRESHWATER, QuantityKind.RATE, "m3/s"),
}


def canonical_unit(layer: ResourceLayer, kind: QuantityKind, gas_basis: str | None = None) -> UnitTag:
    base = CANONICAL_UNITS[(layer, kind)]
    if layer is ResourceLayer.NATURAL_GAS:
        return UnitTag(layer, kind, base.symbol, gas_basis or base.gas_basis)
    return base


@dataclass(frozen=True)
class ExactUncertainty:
    kind: UncertaintyKind = UncertaintyKind.EXACT


@dataclass(frozen=True)
class IntervalUncertainty:
    lower: Fraction
    upper: Fraction
    kind: UncertaintyKind = UncertaintyKind.INTERVAL

    def __post_init__(self):
        if self.lower > self.upper:
            raise ValueError("interval lower > upper")


@dataclass(frozen=True)
class MomentUncertainty:
    mean: Fraction
    variance: Fraction
    kind: UncertaintyKind = UncertaintyKind.MOMENT


@dataclass(frozen=True)
class EmpiricalUncertainty:
    samples: tuple[Fraction, ...]
    alignment_ref: str | None
    kind: UncertaintyKind = UncertaintyKind.EMPIRICAL


@dataclass(frozen=True)
class UnknownUncertainty:
    kind: UncertaintyKind = UncertaintyKind.UNKNOWN


Uncertainty = ExactUncertainty | IntervalUncertainty | MomentUncertainty | EmpiricalUncertainty | UnknownUncertainty


@dataclass(frozen=True)
class QualifiedValue:
    value: Fraction | None
    unit: UnitTag
    interval_id: str
    status: EpistemicStatus = EpistemicStatus.OBSERVED
    uncertainty: Uncertainty = field(default_factory=ExactUncertainty)
    evidence_refs: tuple[str, ...] = ()
    transform_chain: tuple[str, ...] = ()
    hold_codes: tuple[str, ...] = ()
    freshness: str | None = None
    space: ValueSpace = ValueSpace.PHYSICAL

    def with_value(self, value: Fraction | None, *, status: EpistemicStatus | None = None, uncertainty: Uncertainty | None = None, transform: str | None = None) -> "QualifiedValue":
        chain = self.transform_chain + ((transform,) if transform else ())
        return QualifiedValue(
            value=value,
            unit=self.unit,
            interval_id=self.interval_id,
            status=status or self.status,
            uncertainty=uncertainty or self.uncertainty,
            evidence_refs=self.evidence_refs,
            transform_chain=chain,
            hold_codes=self.hold_codes,
            freshness=self.freshness,
            space=self.space,
        )


def qv(value: int | float | str | Fraction | None, layer: ResourceLayer, *, kind: QuantityKind = QuantityKind.RATE,
       interval_id: str = "T0", status: EpistemicStatus = EpistemicStatus.OBSERVED,
       uncertainty: Uncertainty | None = None, gas_basis: str | None = None,
       evidence_refs: Iterable[str] = (), transform_chain: Iterable[str] = (),
       space: ValueSpace = ValueSpace.PHYSICAL) -> QualifiedValue:
    return QualifiedValue(
        value=None if value is None else F(value),
        unit=canonical_unit(layer, kind, gas_basis),
        interval_id=interval_id,
        status=status,
        uncertainty=uncertainty or ExactUncertainty(),
        evidence_refs=tuple(evidence_refs),
        transform_chain=tuple(transform_chain),
        space=space,
    )


@dataclass(frozen=True)
class NodeManifest:
    node_id: str
    layer: ResourceLayer
    node_class: str
    manifest_version: str = "V1"


@dataclass(frozen=True)
class InternalEdgeManifest:
    edge_id: str
    layer: ResourceLayer
    source_node_id: str
    target_node_id: str
    manifest_version: str = "V1"
    loss_model_ref: str | None = None


@dataclass(frozen=True)
class BoundaryEdgeManifest:
    boundary_edge_id: str
    layer: ResourceLayer
    local_node_id: str
    direction: str  # IMPORT or EXPORT
    manifest_version: str = "V1"


@dataclass(frozen=True)
class StorageManifest:
    storage_id: str
    layer: ResourceLayer
    host_node_id: str
    capacity: Fraction
    max_charge_rate: Fraction
    max_discharge_rate: Fraction
    eta_charge: Fraction
    eta_discharge: Fraction
    manifest_version: str = "V1"


@dataclass(frozen=True)
class ProcessCoefficient:
    layer: ResourceLayer
    node_id: str
    coefficient: Fraction
    evidence_ref: str
    coefficient_unit: str


@dataclass(frozen=True)
class ProcessManifest:
    process_id: str
    process_class: str
    activity_unit: str
    coefficient_rows: tuple[ProcessCoefficient, ...]
    source_ref: str
    method_ref: str
    manifest_version: str = "V1"


@dataclass(frozen=True)
class TimeBasis:
    interval_id: str
    delta_t: Fraction

    def __post_init__(self):
        if self.delta_t <= 0:
            raise ValueError("delta_t must be positive")


def qualified_value_guard(v: QualifiedValue, policy: GuardPolicy = GuardPolicy.STRICT_CURRENT_OBSERVED_OR_DERIVED) -> QualifiedValue:
    if any(t.startswith("imputation:") for t in v.transform_chain) and v.status is not EpistemicStatus.IMPUTED:
        raise HoldError(HoldCode.HOLD_IMPUTED_FLAG_ERASED)
    if v.space in (ValueSpace.AUDIT, ValueSpace.EVIDENCE):
        raise HoldError(HoldCode.HOLD_AUDIT_PHYSICAL_MIX)
    if v.space is ValueSpace.STRESS:
        raise HoldError(HoldCode.HOLD_STRESS_PHYSICAL_MIX)
    if v.status is EpistemicStatus.CONFLICTED:
        raise HoldError(HoldCode.HOLD_CONFLICTED_INPUT)
    if v.status is EpistemicStatus.MISSING:
        raise HoldError(HoldCode.HOLD_MISSING_INPUT)
    if v.status is EpistemicStatus.OUT_OF_SCOPE:
        raise HoldError(HoldCode.HOLD_OUT_OF_SCOPE_INPUT)
    if v.status is EpistemicStatus.STALE and policy is not GuardPolicy.ALLOW_STALE_WITH_MAX_AGE:
        raise HoldError(HoldCode.HOLD_STALE_INPUT)
    if v.status is EpistemicStatus.IMPUTED and policy is GuardPolicy.STRICT_CURRENT_OBSERVED_OR_DERIVED:
        raise HoldError(HoldCode.HOLD_IMPUTED_INPUT)
    if v.value is None:
        raise HoldError(HoldCode.HOLD_MISSING_INPUT)
    return v


def ensure_same_rate_signature(values: Iterable[QualifiedValue], layer: ResourceLayer, interval_id: str) -> None:
    gas_basis_seen: set[str] = set()
    for v in values:
        qualified_value_guard(v, GuardPolicy.ALLOW_IMPUTED_WITH_FLAG)
        if v.unit.layer is not layer or v.unit.kind is not QuantityKind.RATE:
            raise HoldError(HoldCode.HOLD_UNIT_MISMATCH)
        if v.interval_id != interval_id:
            raise HoldError(HoldCode.HOLD_TIME_BASIS_MISMATCH)
        if layer is ResourceLayer.NATURAL_GAS:
            gas_basis_seen.add(v.unit.gas_basis or "")
    if len(gas_basis_seen) > 1:
        raise HoldError(HoldCode.HOLD_HHV_LHV_BASIS_MISMATCH)


def validate_topology(nodes: Sequence[NodeManifest], internal_edges: Sequence[InternalEdgeManifest], layer: ResourceLayer, manifest_version: str) -> None:
    ids = {n.node_id for n in nodes if n.layer is layer}
    if len(ids) != len(nodes):
        raise HoldError(HoldCode.HOLD_MANIFEST_MISMATCH)
    for n in nodes:
        if n.layer is not layer:
            raise HoldError(HoldCode.HOLD_MANIFEST_MISMATCH)
        if n.manifest_version != manifest_version:
            raise HoldError(HoldCode.HOLD_TOPOLOGY_CHANGED)
    for e in internal_edges:
        if e.layer is not layer or e.source_node_id not in ids or e.target_node_id not in ids:
            raise HoldError(HoldCode.HOLD_MANIFEST_MISMATCH)
        if e.manifest_version != manifest_version:
            raise HoldError(HoldCode.HOLD_TOPOLOGY_CHANGED)


def build_internal_incidence(nodes: Sequence[NodeManifest], edges: Sequence[InternalEdgeManifest]) -> list[list[Fraction]]:
    idx = {n.node_id: i for i, n in enumerate(nodes)}
    B = [[Fraction(0) for _ in edges] for _ in nodes]
    for j, e in enumerate(edges):
        B[idx[e.source_node_id]][j] = Fraction(-1)
        B[idx[e.target_node_id]][j] = Fraction(1)
    return B


def validate_internal_incidence(B: Sequence[Sequence[Fraction]], nodes: Sequence[NodeManifest], edges: Sequence[InternalEdgeManifest]) -> None:
    expected = build_internal_incidence(nodes, edges)
    if [[F(x) for x in row] for row in B] != expected:
        raise HoldError(HoldCode.HOLD_MANIFEST_MISMATCH)
    if not B:
        return
    for j in range(len(edges)):
        if sum(F(B[i][j]) for i in range(len(nodes))) != 0:
            raise HoldError(HoldCode.HOLD_MANIFEST_MISMATCH)


def boundary_import_export(nodes: Sequence[NodeManifest], edges: Sequence[BoundaryEdgeManifest], flows: Sequence[QualifiedValue], *, layer: ResourceLayer, interval_id: str, manifest_version: str = "V1") -> tuple[dict[str, Fraction], dict[str, Fraction], dict[str, Fraction]]:
    ids = {n.node_id for n in nodes}
    if len(edges) != len(flows):
        raise HoldError(HoldCode.HOLD_MANIFEST_MISMATCH)
    imports = {n.node_id: Fraction(0) for n in nodes}
    exports = {n.node_id: Fraction(0) for n in nodes}
    for e, f in zip(edges, flows):
        if e.manifest_version != manifest_version:
            raise HoldError(HoldCode.HOLD_TOPOLOGY_CHANGED)
        if e.layer is not layer or e.local_node_id not in ids:
            raise HoldError(HoldCode.HOLD_MANIFEST_MISMATCH)
        ensure_same_rate_signature([f], layer, interval_id)
        assert f.value is not None
        if f.value < 0:
            raise HoldError(HoldCode.HOLD_NEGATIVE_DIRECTED_FLOW)
        if e.direction == "IMPORT":
            imports[e.local_node_id] += f.value
        elif e.direction == "EXPORT":
            exports[e.local_node_id] += f.value
        else:
            raise HoldError(HoldCode.HOLD_BOUNDARY_DIRECTION)
    net = {nid: imports[nid] - exports[nid] for nid in ids}
    return imports, exports, net


def process_coupling(process: ProcessManifest, activity: QualifiedValue, target_nodes: Sequence[NodeManifest], *, target_layer: ResourceLayer, interval_id: str) -> dict[str, Fraction]:
    if process.process_class.upper() in {"CORRELATION", "ASSOCIATION", "EDITORIAL"}:
        raise HoldError(HoldCode.HOLD_CAUSALITY)
    if not process.source_ref or not process.method_ref:
        raise HoldError(HoldCode.HOLD_PROCESS_EVIDENCE)
    qualified_value_guard(activity, GuardPolicy.ALLOW_IMPUTED_WITH_FLAG)
    if activity.interval_id != interval_id:
        raise HoldError(HoldCode.HOLD_TIME_BASIS_MISMATCH)
    if activity.value is None:
        raise HoldError(HoldCode.HOLD_MISSING_INPUT)
    out = {n.node_id: Fraction(0) for n in target_nodes if n.layer is target_layer}
    for row in process.coefficient_rows:
        if not row.evidence_ref:
            raise HoldError(HoldCode.HOLD_PROCESS_EVIDENCE)
        if not row.coefficient_unit:
            raise HoldError(HoldCode.HOLD_PROCESS_UNIT)
        if row.layer is target_layer:
            if row.node_id not in out:
                raise HoldError(HoldCode.HOLD_PROCESS_SCOPE)
            out[row.node_id] += row.coefficient * activity.value
    return out


def resource_balance_residual(*, layer: ResourceLayer, interval_id: str, nodes: Sequence[NodeManifest], internal_edges: Sequence[InternalEdgeManifest], B: Sequence[Sequence[Fraction]], production: Sequence[QualifiedValue], demand: Sequence[QualifiedValue], loss: Sequence[QualifiedValue], internal_flow: Sequence[QualifiedValue], boundary_edges: Sequence[BoundaryEdgeManifest] = (), boundary_flow: Sequence[QualifiedValue] = (), storage_delta_rate: Sequence[QualifiedValue] | None = None, process_contribution: Mapping[str, Fraction] | None = None, manifest_version: str = "V1") -> dict[str, Fraction]:
    validate_topology(nodes, internal_edges, layer, manifest_version)
    validate_internal_incidence(B, nodes, internal_edges)
    n = len(nodes)
    if not (len(production) == len(demand) == len(loss) == n):
        raise HoldError(HoldCode.HOLD_MANIFEST_MISMATCH)
    if len(internal_flow) != len(internal_edges):
        raise HoldError(HoldCode.HOLD_MANIFEST_MISMATCH)
    values = list(production) + list(demand) + list(loss) + list(internal_flow)
    if storage_delta_rate:
        values += list(storage_delta_rate)
    ensure_same_rate_signature(values, layer, interval_id)
    if any(e.loss_model_ref for e in internal_edges) and any(v.value not in (None, 0) for v in loss):
        raise HoldError(HoldCode.HOLD_DOUBLE_COUNT_LOSS)
    _, _, boundary_net = boundary_import_export(nodes, boundary_edges, boundary_flow, layer=layer, interval_id=interval_id, manifest_version=manifest_version) if boundary_edges else ({}, {}, {n.node_id: Fraction(0) for n in nodes})
    proc = {n.node_id: Fraction(0) for n in nodes}
    if process_contribution:
        for nid, val in process_contribution.items():
            if nid not in proc:
                raise HoldError(HoldCode.HOLD_PROCESS_SCOPE)
            proc[nid] += F(val)
    storage = [Fraction(0)] * n
    if storage_delta_rate:
        if len(storage_delta_rate) != n:
            raise HoldError(HoldCode.HOLD_MANIFEST_MISMATCH)
        storage = [v.value or Fraction(0) for v in storage_delta_rate]
    res = {}
    for i, node in enumerate(nodes):
        pv, dv, lv = production[i].value, demand[i].value, loss[i].value
        assert pv is not None and dv is not None and lv is not None
        transport = sum(F(B[i][j]) * (internal_flow[j].value or 0) for j in range(len(internal_edges)))
        res[node.node_id] = pv - dv - lv + transport + boundary_net.get(node.node_id, 0) + storage[i] + proc[node.node_id]
    return res


def storage_transition(storage: StorageManifest, time_basis: TimeBasis, stock: QualifiedValue, charge: QualifiedValue, discharge: QualifiedValue, *, self_loss_rate: Fraction = Fraction(0)) -> QualifiedValue:
    ensure_same_rate_signature([charge, discharge], storage.layer, time_basis.interval_id)
    qualified_value_guard(stock, GuardPolicy.ALLOW_IMPUTED_WITH_FLAG)
    if stock.unit.layer is not storage.layer or stock.unit.kind is not QuantityKind.STOCK:
        raise HoldError(HoldCode.HOLD_UNIT_MISMATCH)
    if stock.interval_id != time_basis.interval_id:
        raise HoldError(HoldCode.HOLD_TIME_BASIS_MISMATCH)
    if not (Fraction(0) < storage.eta_charge <= 1 and Fraction(0) < storage.eta_discharge <= 1):
        raise HoldError(HoldCode.HOLD_EFFICIENCY_DOMAIN)
    assert stock.value is not None and charge.value is not None and discharge.value is not None
    if charge.value > storage.max_charge_rate or discharge.value > storage.max_discharge_rate:
        raise HoldError(HoldCode.HOLD_STORAGE_RATE)
    nxt = stock.value + time_basis.delta_t * (storage.eta_charge * charge.value - discharge.value / storage.eta_discharge - self_loss_rate)
    if nxt < 0 or nxt > storage.capacity:
        raise HoldError(HoldCode.HOLD_STORAGE_CAPACITY)
    return QualifiedValue(nxt, stock.unit, time_basis.interval_id, EpistemicStatus.DERIVED, ExactUncertainty(), stock.evidence_refs + charge.evidence_refs + discharge.evidence_refs, stock.transform_chain + ("storage_transition",), space=ValueSpace.PHYSICAL)


def uncertainty_propagate(coefficients: Sequence[Fraction], uncertainties: Sequence[Uncertainty], *, covariance: Sequence[Sequence[Fraction]] | None = None, sample_alignment_ref: str | None = None) -> Uncertainty:
    if len(coefficients) != len(uncertainties):
        raise HoldError(HoldCode.HOLD_UNCERTAINTY_OPERATOR)
    if all(isinstance(u, ExactUncertainty) for u in uncertainties):
        return ExactUncertainty()
    if all(isinstance(u, (ExactUncertainty, IntervalUncertainty)) for u in uncertainties):
        lo = Fraction(0)
        hi = Fraction(0)
        for a, u in zip(coefficients, uncertainties):
            if isinstance(u, ExactUncertainty):
                l = h = Fraction(0)
            else:
                l, h = u.lower, u.upper
            vals = (a * l, a * h)
            lo += min(vals)
            hi += max(vals)
        return IntervalUncertainty(lo, hi)
    if all(isinstance(u, MomentUncertainty) for u in uncertainties):
        if covariance is None:
            raise HoldError(HoldCode.HOLD_COVARIANCE_REQUIRED)
        mean = sum(a * u.mean for a, u in zip(coefficients, uncertainties) if isinstance(u, MomentUncertainty))
        var = Fraction(0)
        for i, ai in enumerate(coefficients):
            for j, aj in enumerate(coefficients):
                var += ai * aj * F(covariance[i][j])
        return MomentUncertainty(mean, var)
    if all(isinstance(u, EmpiricalUncertainty) for u in uncertainties):
        emps = [u for u in uncertainties if isinstance(u, EmpiricalUncertainty)]
        if not sample_alignment_ref or any(u.alignment_ref != sample_alignment_ref for u in emps):
            raise HoldError(HoldCode.HOLD_SAMPLE_ALIGNMENT_REQUIRED)
        sizes = {len(u.samples) for u in emps}
        if len(sizes) != 1:
            raise HoldError(HoldCode.HOLD_SAMPLE_ALIGNMENT_REQUIRED)
        out = tuple(sum(a * emps[i].samples[j] for i, a in enumerate(coefficients)) for j in range(next(iter(sizes))))
        return EmpiricalUncertainty(out, sample_alignment_ref)
    return UnknownUncertainty()


def audit_vector_l1_l4(l1: Fraction, l2: Fraction, l3: Fraction, l4: Fraction) -> tuple[Fraction, Fraction, Fraction, Fraction]:
    vals = tuple(F(x) for x in (l1, l2, l3, l4))
    if any(x < 0 or x > 1 for x in vals):
        raise ValueError("audit component outside [0,1]")
    return vals  # deliberately no weighted scalar


def emit_aggregate_equilibrium_score(*args: Any, **kwargs: Any) -> None:
    raise HoldError(HoldCode.HOLD_AGGREGATE_SCORE_PROHIBITED)


def canonical_json(obj: Any) -> str:
    def conv(x: Any) -> Any:
        if isinstance(x, Fraction):
            return {"n": x.numerator, "d": x.denominator}
        if isinstance(x, Enum):
            return x.value
        if hasattr(x, "__dataclass_fields__"):
            return {k: conv(getattr(x, k)) for k in sorted(x.__dataclass_fields__)}
        if isinstance(x, Mapping):
            return {str(k): conv(v) for k, v in sorted(x.items(), key=lambda kv: str(kv[0]))}
        if isinstance(x, (list, tuple)):
            return [conv(v) for v in x]
        return x
    return json.dumps(conv(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_sha256(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


# ---------------- Synthetic fixtures ----------------

def nodes_for(layer: ResourceLayer, names: Sequence[str], version: str = "V1") -> list[NodeManifest]:
    cls = {
        ResourceLayer.ELECTRICITY: "ELECTRICITY_ZONE",
        ResourceLayer.NATURAL_GAS: "GAS_ZONE",
        ResourceLayer.CRUDE_OIL: "OIL_ZONE_OR_HUB",
        ResourceLayer.FRESHWATER: "WATER_BASIN_OR_ACCOUNTING_UNIT",
    }[layer]
    return [NodeManifest(n, layer, cls, version) for n in names]


def fixture_f01():
    layer = ResourceLayer.ELECTRICITY
    nodes = nodes_for(layer, ["E0", "E1"])
    edges = [InternalEdgeManifest("E01", layer, "E0", "E1")]
    B = build_internal_incidence(nodes, edges)
    return dict(layer=layer, interval_id="T0", nodes=nodes, internal_edges=edges, B=B,
                production=[qv(15, layer), qv(0, layer)], demand=[qv(5, layer), qv(10, layer)],
                loss=[qv(0, layer), qv(0, layer)], internal_flow=[qv(10, layer)])


def fixture_f02():
    layer = ResourceLayer.ELECTRICITY
    nodes = nodes_for(layer, ["E0"])
    edges: list[InternalEdgeManifest] = []
    return dict(layer=layer, interval_id="T0", nodes=nodes, internal_edges=edges, B=[[]],
                production=[qv(0, layer)], demand=[qv(5, layer)], loss=[qv(0, layer)], internal_flow=[],
                boundary_edges=[BoundaryEdgeManifest("BIN", layer, "E0", "IMPORT")], boundary_flow=[qv(5, layer)])


def fixture_f03_process_gas():
    layer = ResourceLayer.NATURAL_GAS
    nodes = nodes_for(layer, ["G0"])
    process = ProcessManifest("GT", "PHYSICAL_CONVERSION", "activity", (ProcessCoefficient(layer, "G0", F(-80), "EV:gas-rate", "W_th/activity"),), "SRC", "METHOD")
    activity = QualifiedValue(F(1), UnitTag(layer, QuantityKind.DIMENSIONLESS, "activity"), "T0")
    contribution = process_coupling(process, activity, nodes, target_layer=layer, interval_id="T0")
    args = dict(layer=layer, interval_id="T0", nodes=nodes, internal_edges=[], B=[[]],
                production=[qv(100, layer)], demand=[qv(20, layer)], loss=[qv(0, layer)], internal_flow=[], process_contribution=contribution)
    return args, process, activity


def fixture_f04_process_electricity():
    layer = ResourceLayer.ELECTRICITY
    nodes = nodes_for(layer, ["E0"])
    process = ProcessManifest("GT", "PHYSICAL_CONVERSION", "activity", (ProcessCoefficient(layer, "E0", F(40), "EV:elec-rate", "W_e/activity"),), "SRC", "METHOD")
    activity = QualifiedValue(F(1), UnitTag(layer, QuantityKind.DIMENSIONLESS, "activity"), "T0")
    contribution = process_coupling(process, activity, nodes, target_layer=layer, interval_id="T0")
    args = dict(layer=layer, interval_id="T0", nodes=nodes, internal_edges=[], B=[[]], production=[qv(0, layer)], demand=[qv(40, layer)], loss=[qv(0, layer)], internal_flow=[], process_contribution=contribution)
    return args


def fixture_f05_process_water():
    layer = ResourceLayer.FRESHWATER
    nodes = nodes_for(layer, ["W0"])
    process = ProcessManifest("GT", "PHYSICAL_CONVERSION", "activity", (ProcessCoefficient(layer, "W0", F(-2), "EV:water-rate", "m3/s/activity"),), "SRC", "METHOD")
    activity = QualifiedValue(F(1), UnitTag(layer, QuantityKind.DIMENSIONLESS, "activity"), "T0")
    contribution = process_coupling(process, activity, nodes, target_layer=layer, interval_id="T0")
    return dict(layer=layer, interval_id="T0", nodes=nodes, internal_edges=[], B=[[]], production=[qv(2, layer)], demand=[qv(0, layer)], loss=[qv(0, layer)], internal_flow=[], process_contribution=contribution)


def fixture_f06_storage():
    layer = ResourceLayer.ELECTRICITY
    st = StorageManifest("S0", layer, "E0", F(200), F(20), F(20), F("0.9"), F("0.8"))
    return st, TimeBasis("T0", F(1)), qv(100, layer, kind=QuantityKind.STOCK), qv(10, layer), qv(4, layer)


def fixture_f07_oil_network():
    layer = ResourceLayer.CRUDE_OIL
    nodes = nodes_for(layer, ["O0", "O1", "O2"])
    edges = [InternalEdgeManifest("O01", layer, "O0", "O1"), InternalEdgeManifest("O12", layer, "O1", "O2")]
    B = build_internal_incidence(nodes, edges)
    return dict(layer=layer, interval_id="T0", nodes=nodes, internal_edges=edges, B=B,
                production=[qv(12, layer), qv(0, layer), qv(0, layer)], demand=[qv(0, layer), qv(0, layer), qv(12, layer)],
                loss=[qv(0, layer)] * 3, internal_flow=[qv(12, layer), qv(12, layer)])


def fixture_f08_desalination():
    en = nodes_for(ResourceLayer.ELECTRICITY, ["E0"])
    wa = nodes_for(ResourceLayer.FRESHWATER, ["W0"])
    proc = ProcessManifest("DESAL", "PHYSICAL_CONVERSION", "activity", (
        ProcessCoefficient(ResourceLayer.ELECTRICITY, "E0", F(-6), "EV:desal-elec", "W_e/activity"),
        ProcessCoefficient(ResourceLayer.FRESHWATER, "W0", F(3), "EV:desal-water", "m3/s/activity"),
    ), "SRC", "METHOD")
    activity = QualifiedValue(F(1), UnitTag(ResourceLayer.ELECTRICITY, QuantityKind.DIMENSIONLESS, "activity"), "T0")
    ce = process_coupling(proc, activity, en, target_layer=ResourceLayer.ELECTRICITY, interval_id="T0")
    cw = process_coupling(proc, activity, wa, target_layer=ResourceLayer.FRESHWATER, interval_id="T0")
    eargs = dict(layer=ResourceLayer.ELECTRICITY, interval_id="T0", nodes=en, internal_edges=[], B=[[]], production=[qv(6, ResourceLayer.ELECTRICITY)], demand=[qv(0, ResourceLayer.ELECTRICITY)], loss=[qv(0, ResourceLayer.ELECTRICITY)], internal_flow=[], process_contribution=ce)
    wargs = dict(layer=ResourceLayer.FRESHWATER, interval_id="T0", nodes=wa, internal_edges=[], B=[[]], production=[qv(0, ResourceLayer.FRESHWATER)], demand=[qv(3, ResourceLayer.FRESHWATER)], loss=[qv(0, ResourceLayer.FRESHWATER)], internal_flow=[], process_contribution=cw)
    return eargs, wargs, proc, activity


def fixture_f09_zero_missing():
    return qv(0, ResourceLayer.ELECTRICITY), qv(None, ResourceLayer.ELECTRICITY, status=EpistemicStatus.MISSING)


def fixture_f10_permutation():
    return fixture_f01()


def fixture_f11_interval():
    return [F(1), F(-1)], [IntervalUncertainty(F(2), F(4)), IntervalUncertainty(F(1), F(3))]


def fixture_f12_moment():
    return [F(2), F(-1)], [MomentUncertainty(F(10), F(4)), MomentUncertainty(F(3), F(9))], [[F(4), F(1)], [F(1), F(9)]]


def fixture_f13_empirical():
    return [F(1), F(2)], [EmpiricalUncertainty((F(1), F(2), F(3)), "A"), EmpiricalUncertainty((F(4), F(5), F(6)), "A")]


def fixture_f14_four_layers():
    out = {}
    for layer, name in [(ResourceLayer.ELECTRICITY,"E0"),(ResourceLayer.NATURAL_GAS,"G0"),(ResourceLayer.CRUDE_OIL,"O0"),(ResourceLayer.FRESHWATER,"W0")]:
        nodes = nodes_for(layer,[name])
        out[layer] = dict(layer=layer, interval_id="T0", nodes=nodes, internal_edges=[], B=[[]], production=[qv(7,layer)], demand=[qv(7,layer)], loss=[qv(0,layer)], internal_flow=[])
    return out


@dataclass(frozen=True)
class ValidationResult:
    id: str
    passed: bool
    observed: str


def _expect_hold(code: HoldCode, fn) -> tuple[bool, str]:
    try:
        fn()
    except HoldError as e:
        return (e.code is code, e.code.value)
    return (False, "NO_HOLD")


def run_validation_matrix() -> list[ValidationResult]:
    results: list[ValidationResult] = []
    def add(i: int, passed: bool, observed: Any):
        results.append(ValidationResult(f"V{i:02d}", bool(passed), str(observed)))

    # 01
    f1 = fixture_f01(); validate_internal_incidence(f1["B"], f1["nodes"], f1["internal_edges"]); add(1, True, "PASS")
    # 02
    r = resource_balance_residual(**f1); add(2, all(v == 0 for v in r.values()), r)
    # 03
    r = resource_balance_residual(**fixture_f02()); add(3, all(v == 0 for v in r.values()), r)
    # 04
    args, _, _ = fixture_f03_process_gas(); r = resource_balance_residual(**args); add(4, all(v == 0 for v in r.values()), r)
    # 05
    r = resource_balance_residual(**fixture_f04_process_electricity()); add(5, all(v == 0 for v in r.values()), r)
    # 06
    r = resource_balance_residual(**fixture_f05_process_water()); add(6, all(v == 0 for v in r.values()), r)
    # 07
    st,tb,s,u,w=fixture_f06_storage(); nxt=storage_transition(st,tb,s,u,w); add(7,nxt.value==F(104),nxt.value)
    # 08
    r=resource_balance_residual(**fixture_f07_oil_network()); add(8,all(v==0 for v in r.values()),r)
    # 09
    ea,wa,_,_=fixture_f08_desalination(); re=resource_balance_residual(**ea); rw=resource_balance_residual(**wa); add(9,all(v==0 for v in re.values()) and all(v==0 for v in rw.values()),(re,rw))
    # 10
    fours=fixture_f14_four_layers(); rr={k:resource_balance_residual(**a) for k,a in fours.items()}; add(10,all(all(v==0 for v in r.values()) for r in rr.values()),rr)
    # 11
    badB=[[F(1)],[F(-1)]]; ok,obs=_expect_hold(HoldCode.HOLD_MANIFEST_MISMATCH,lambda:resource_balance_residual(**{**fixture_f01(),"B":badB})); add(11,ok,obs)
    # 12
    f=fixture_f02(); bad_edges=[BoundaryEdgeManifest("BIN",ResourceLayer.ELECTRICITY,"E0","SIDEWAYS")]; ok,obs=_expect_hold(HoldCode.HOLD_BOUNDARY_DIRECTION,lambda:resource_balance_residual(**{**f,"boundary_edges":bad_edges})); add(12,ok,obs)
    # 13
    args,proc,activity=fixture_f03_process_gas(); badproc=ProcessManifest(proc.process_id,proc.process_class,proc.activity_unit,(ProcessCoefficient(ResourceLayer.NATURAL_GAS,"G0",F(80),"EV","W_th/activity"),),proc.source_ref,proc.method_ref); badc=process_coupling(badproc,activity,args["nodes"],target_layer=ResourceLayer.NATURAL_GAS,interval_id="T0"); badr=resource_balance_residual(**{**args,"process_contribution":badc}); add(13,any(v!=0 for v in badr.values()),badr)
    # 14
    wrong=qv(1,ResourceLayer.FRESHWATER); ff=fixture_f01(); ok,obs=_expect_hold(HoldCode.HOLD_UNIT_MISMATCH,lambda:resource_balance_residual(**{**ff,"production":[wrong,ff["production"][1]]})); add(14,ok,obs)
    # 15
    stock_as_rate=qv(15,ResourceLayer.ELECTRICITY,kind=QuantityKind.STOCK); ok,obs=_expect_hold(HoldCode.HOLD_UNIT_MISMATCH,lambda:resource_balance_residual(**{**ff,"production":[stock_as_rate,ff["production"][1]]})); add(15,ok,obs)
    # 16
    gasnodes=nodes_for(ResourceLayer.NATURAL_GAS,["G0"]); gasargs=dict(layer=ResourceLayer.NATURAL_GAS,interval_id="T0",nodes=gasnodes,internal_edges=[],B=[[]],production=[qv(1,ResourceLayer.NATURAL_GAS,gas_basis="HHV")],demand=[qv(1,ResourceLayer.NATURAL_GAS,gas_basis="LHV")],loss=[qv(0,ResourceLayer.NATURAL_GAS,gas_basis="HHV")],internal_flow=[]); ok,obs=_expect_hold(HoldCode.HOLD_HHV_LHV_BASIS_MISMATCH,lambda:resource_balance_residual(**gasargs)); add(16,ok,obs)
    # 17
    badtime=qv(5,ResourceLayer.ELECTRICITY,interval_id="T1"); f2=fixture_f02(); ok,obs=_expect_hold(HoldCode.HOLD_TIME_BASIS_MISMATCH,lambda:resource_balance_residual(**{**f2,"demand":[badtime]})); add(17,ok,obs)
    # 18
    st,tb,s,u,w=fixture_f06_storage(); small=StorageManifest(st.storage_id,st.layer,st.host_node_id,F(103),st.max_charge_rate,st.max_discharge_rate,st.eta_charge,st.eta_discharge); ok,obs=_expect_hold(HoldCode.HOLD_STORAGE_CAPACITY,lambda:storage_transition(small,tb,s,u,w)); add(18,ok,obs)
    # 19
    ok,obs=_expect_hold(HoldCode.HOLD_STORAGE_RATE,lambda:storage_transition(st,tb,s,qv(21,st.layer),w)); add(19,ok,obs)
    # 20
    ok,obs=_expect_hold(HoldCode.HOLD_STORAGE_RATE,lambda:storage_transition(st,tb,s,u,qv(21,st.layer))); add(20,ok,obs)
    # 21
    badeta=StorageManifest(st.storage_id,st.layer,st.host_node_id,st.capacity,st.max_charge_rate,st.max_discharge_rate,F(0),st.eta_discharge); ok,obs=_expect_hold(HoldCode.HOLD_EFFICIENCY_DOMAIN,lambda:storage_transition(badeta,tb,s,u,w)); add(21,ok,obs)
    # 22
    zero,missing=fixture_f09_zero_missing(); z_ok=qualified_value_guard(zero).value==0; h,obs=_expect_hold(HoldCode.HOLD_MISSING_INPUT,lambda:qualified_value_guard(missing)); add(22,z_ok and h,obs)
    # 23
    conflicted=qv(3,ResourceLayer.ELECTRICITY,status=EpistemicStatus.CONFLICTED); h,obs=_expect_hold(HoldCode.HOLD_CONFLICTED_INPUT,lambda:qualified_value_guard(conflicted)); add(23,h,obs)
    # 24
    stale=qv(3,ResourceLayer.ELECTRICITY,status=EpistemicStatus.STALE); h,obs=_expect_hold(HoldCode.HOLD_STALE_INPUT,lambda:qualified_value_guard(stale)); add(24,h,obs)
    # 25
    erased=qv(3,ResourceLayer.ELECTRICITY,status=EpistemicStatus.DERIVED,transform_chain=["imputation:model-x"]); h,obs=_expect_hold(HoldCode.HOLD_IMPUTED_FLAG_ERASED,lambda:qualified_value_guard(erased,GuardPolicy.ALLOW_IMPUTED_WITH_FLAG)); add(25,h,obs)
    # 26
    coeff,unc,cov=fixture_f12_moment(); h,obs=_expect_hold(HoldCode.HOLD_COVARIANCE_REQUIRED,lambda:uncertainty_propagate(coeff,unc)); add(26,h,obs)
    # 27
    coeff,unc=fixture_f13_empirical(); bad=[EmpiricalUncertainty(unc[0].samples,"A"),EmpiricalUncertainty(unc[1].samples,"B")]; h,obs=_expect_hold(HoldCode.HOLD_SAMPLE_ALIGNMENT_REQUIRED,lambda:uncertainty_propagate(coeff,bad,sample_alignment_ref="A")); add(27,h,obs)
    # 28
    ff=fixture_f01(); edges=[InternalEdgeManifest("E01",ResourceLayer.ELECTRICITY,"E0","E1",loss_model_ref="LOSS")]; h,obs=_expect_hold(HoldCode.HOLD_DOUBLE_COUNT_LOSS,lambda:resource_balance_residual(**{**ff,"internal_edges":edges,"B":build_internal_incidence(ff["nodes"],edges),"loss":[qv(1,ResourceLayer.ELECTRICITY),qv(0,ResourceLayer.ELECTRICITY)]})); add(28,h,obs)
    # 29
    args,proc,activity=fixture_f03_process_gas(); badp=ProcessManifest(proc.process_id,proc.process_class,proc.activity_unit,(ProcessCoefficient(ResourceLayer.NATURAL_GAS,"G0",F(-80),"","W_th/activity"),),proc.source_ref,proc.method_ref); h,obs=_expect_hold(HoldCode.HOLD_PROCESS_EVIDENCE,lambda:process_coupling(badp,activity,args["nodes"],target_layer=ResourceLayer.NATURAL_GAS,interval_id="T0")); add(29,h,obs)
    # 30
    corr=ProcessManifest("C","CORRELATION","activity",(),"SRC","METHOD"); h,obs=_expect_hold(HoldCode.HOLD_CAUSALITY,lambda:process_coupling(corr,activity,args["nodes"],target_layer=ResourceLayer.NATURAL_GAS,interval_id="T0")); add(30,h,obs)
    # 31
    audit=qv(15,ResourceLayer.ELECTRICITY,space=ValueSpace.AUDIT); ff=fixture_f01(); h,obs=_expect_hold(HoldCode.HOLD_AUDIT_PHYSICAL_MIX,lambda:resource_balance_residual(**{**ff,"production":[audit,ff["production"][1]]})); add(31,h,obs)
    # 32
    evid=qv(15,ResourceLayer.ELECTRICITY,space=ValueSpace.EVIDENCE); h,obs=_expect_hold(HoldCode.HOLD_AUDIT_PHYSICAL_MIX,lambda:resource_balance_residual(**{**ff,"production":[evid,ff["production"][1]]})); add(32,h,obs)
    # 33
    stress=qv(15,ResourceLayer.ELECTRICITY,space=ValueSpace.STRESS); h,obs=_expect_hold(HoldCode.HOLD_STRESS_PHYSICAL_MIX,lambda:resource_balance_residual(**{**ff,"production":[stress,ff["production"][1]]})); add(33,h,obs)
    # 34
    h,obs=_expect_hold(HoldCode.HOLD_AGGREGATE_SCORE_PROHIBITED,lambda:emit_aggregate_equilibrium_score([1,2])); add(34,h,obs)
    # 35
    ff=fixture_f01(); badnodes=[NodeManifest("E0",ResourceLayer.ELECTRICITY,"ELECTRICITY_ZONE","V2"),ff["nodes"][1]]; h,obs=_expect_hold(HoldCode.HOLD_TOPOLOGY_CHANGED,lambda:resource_balance_residual(**{**ff,"nodes":badnodes})); add(35,h,obs)
    # 36
    r1=resource_balance_residual(**fixture_f01()); r2=resource_balance_residual(**fixture_f01()); add(36,canonical_sha256(r1)==canonical_sha256(r2),(canonical_sha256(r1),canonical_sha256(r2)))
    # 37
    base=resource_balance_residual(**fixture_f01()); layer=ResourceLayer.ELECTRICITY; nodes=nodes_for(layer,["E1","E0"]); edges=[InternalEdgeManifest("E01",layer,"E0","E1")]; B=build_internal_incidence(nodes,edges); perm=dict(layer=layer,interval_id="T0",nodes=nodes,internal_edges=edges,B=B,production=[qv(0,layer),qv(15,layer)],demand=[qv(10,layer),qv(5,layer)],loss=[qv(0,layer),qv(0,layer)],internal_flow=[qv(10,layer)]); pr=resource_balance_residual(**perm); add(37,base==pr,(base,pr))
    # 38
    zero,missing=fixture_f09_zero_missing(); explicit=(qualified_value_guard(zero).value==0); mh,_=_expect_hold(HoldCode.HOLD_MISSING_INPUT,lambda:qualified_value_guard(missing)); add(38,explicit and mh,"DISTINCT")
    # 39
    args,proc,activity=fixture_f03_process_gas(); enodes=nodes_for(ResourceLayer.ELECTRICITY,["E0"]); out=process_coupling(proc,activity,enodes,target_layer=ResourceLayer.ELECTRICITY,interval_id="T0"); add(39,all(v==0 for v in out.values()),out)
    # 40
    a=resource_balance_residual(**fixture_f01()); _=resource_balance_residual(**fixture_f07_oil_network()); b=resource_balance_residual(**fixture_f01()); add(40,a==b,(a,b))
    return results


def validation_receipt(results: Sequence[ValidationResult]) -> dict[str, Any]:
    return {
        "gate_id": GATE_ID,
        "contract_version": CONTRACT_VERSION,
        "hgraph_native_available": HGRAPH_NATIVE_AVAILABLE,
        "operator_set": [
            "resource_balance_residual",
            "storage_transition",
            "process_coupling",
            "boundary_import_export",
            "qualified_value_guard",
            "uncertainty_propagate",
            "audit_vector_l1_l4",
        ],
        "validation_count": len(results),
        "pass_count": sum(r.passed for r in results),
        "results": [r.__dict__ for r in results],
        "claim_ceiling": {
            "real_world_data_bind": False,
            "ui": False,
            "aggregate_eq_score": "HOLD_PROHIBITED",
            "runtime_admission": False,
            "global_bind": False,
            "native_hgraph_binding": "HOLD_NOT_AVAILABLE_IN_EXECUTION_ENVIRONMENT",
        },
    }


if __name__ == "__main__":
    results = run_validation_matrix()
    receipt = validation_receipt(results)
    print(canonical_json(receipt))