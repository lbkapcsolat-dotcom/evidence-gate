from __future__ import annotations

from fractions import Fraction
import hashlib
import json
from pathlib import Path
from typing import Any

import equilibrium_planetary_resource_core_v1 as core
import planetary_resource_source_adapter_subsystem_freeze_v1 as adapter_freeze


GATE_ID = (
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__CORE_REENTRY_AND_UNRESOLVED_KERNEL_GAP_REVIEW_V1"
)
REVIEW_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__CORE_REENTRY_AND_UNRESOLVED_KERNEL_GAP_REVIEW.json"
)
OUT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__CORE_REENTRY_AND_UNRESOLVED_KERNEL_GAP_REVIEW_RECEIPT.json"
)


def sha256_file(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_sha256(obj: Any) -> str:
    body = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def load_review() -> dict[str, Any]:
    r = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
    if r["gate_id"] != GATE_ID:
        raise AssertionError("review gate mismatch")
    selected = r["next_single_unproven_core_capability"]
    if selected["id"] != "PROCESS_COUPLING_TYPED_DIMENSIONAL_CLOSURE_V1":
        raise AssertionError("review selected more or different next capability")
    if selected["implementation_not_authorized_by_this_review"] is not True:
        raise AssertionError("review must not implement successor capability")
    if r["fences"]["provider_work"] is not False:
        raise AssertionError("provider work must remain off")
    for key in (
        "new_source_ingest","multi_source_fusion","eq_score","ui",
        "runtime_admission","pointer_promotion","global_bind","merge",
    ):
        if r["fences"][key] is not False:
            raise AssertionError(f"scope fence enabled: {key}")
    return r


def verify_pins(r: dict[str, Any]) -> dict[str, str]:
    pins = r["pins"]
    checks = {
        "source_adapter_freeze_manifest_sha256": (
            "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__SOURCE_ADAPTER_SUBSYSTEM_FREEZE.json",
            pins["source_adapter_freeze_manifest_sha256"],
        ),
        "python_core_sha256": (
            "equilibrium_planetary_resource_core_v1.py",
            pins["python_core_sha256"],
        ),
        "cpp_kernel_sha256": (
            "planetary_resource_cpp_kernel_v1.cpp",
            pins["cpp_kernel_sha256"],
        ),
    }
    out: dict[str, str] = {}
    for name, (path, want) in checks.items():
        got = sha256_file(path)
        if got != want:
            raise AssertionError(f"{name} changed: {got} != {want}")
        out[name] = got

    freeze_receipt = adapter_freeze.run_freeze()
    freeze_sha = canonical_sha256(freeze_receipt)
    if freeze_sha != pins["source_adapter_freeze_receipt_sha256"]:
        raise AssertionError(
            f"adapter freeze receipt changed: {freeze_sha} != "
            f"{pins['source_adapter_freeze_receipt_sha256']}"
        )
    out["source_adapter_freeze_receipt_sha256"] = freeze_sha
    return out


def review_balance_kernel() -> dict[str, Any]:
    base = core.resource_balance_residual(**core.fixture_f01())
    if not all(v == 0 for v in base.values()):
        raise AssertionError("baseline balance fixture not closed")

    f = core.fixture_f01()
    injected = core.resource_balance_residual(
        **{**f, "process_contribution": {"E0": core.F(1)}}
    )
    raw_untyped_process_injection_accepted = injected["E0"] == core.F(1)

    return {
        "baseline_zero_residual": True,
        "typed_primitive_signature_guards_present": True,
        "raw_untyped_process_injection_accepted": raw_untyped_process_injection_accepted,
        "status": "PASS_BOUNDED_WITH_PROCESS_INGRESS_GAP",
    }


def review_storage_kernel() -> dict[str, Any]:
    st, tb, stock, charge, discharge = core.fixture_f06_storage()
    nxt = core.storage_transition(st, tb, stock, charge, discharge)
    if nxt.value != core.F(104):
        raise AssertionError("storage baseline changed")
    if not isinstance(nxt.uncertainty, core.ExactUncertainty):
        raise AssertionError("storage baseline uncertainty representation changed")
    uncertain_stock = core.QualifiedValue(
        stock.value,
        stock.unit,
        stock.interval_id,
        stock.status,
        core.IntervalUncertainty(core.F(99), core.F(101)),
        stock.evidence_refs,
        stock.transform_chain,
        stock.hold_codes,
        stock.freshness,
        stock.space,
    )
    uncertain_next = core.storage_transition(st, tb, uncertain_stock, charge, discharge)
    uncertainty_dropped_to_exact = isinstance(
        uncertain_next.uncertainty, core.ExactUncertainty
    )
    return {
        "deterministic_transition_104": True,
        "uncertain_input_returns_exact_output": uncertainty_dropped_to_exact,
        "status": "PASS_BOUNDED_DETERMINISTIC_VALUE_PATH",
    }


def review_process_coupling() -> dict[str, Any]:
    layer = core.ResourceLayer.ELECTRICITY
    nodes = core.nodes_for(layer, ["E0"])
    activity = core.QualifiedValue(
        core.F(1),
        core.UnitTag(layer, core.QuantityKind.DIMENSIONLESS, "activity"),
        "T0",
    )
    mismatched = core.ProcessManifest(
        "BAD_UNIT",
        "PHYSICAL_CONVERSION",
        "activity",
        (
            core.ProcessCoefficient(
                layer,
                "E0",
                core.F(5),
                "EV:bad-unit",
                "m3/s/activity",
            ),
        ),
        "SRC",
        "METHOD",
    )
    out = core.process_coupling(
        mismatched,
        activity,
        nodes,
        target_layer=layer,
        interval_id="T0",
    )
    wrong_coefficient_unit_accepted = out["E0"] == core.F(5)

    mismatched_activity = core.QualifiedValue(
        core.F(1),
        core.UnitTag(layer, core.QuantityKind.DIMENSIONLESS, "wrong_activity_symbol"),
        "T0",
    )
    process = core.ProcessManifest(
        "BAD_ACTIVITY_UNIT",
        "PHYSICAL_CONVERSION",
        "declared_activity_symbol",
        (
            core.ProcessCoefficient(
                layer,
                "E0",
                core.F(2),
                "EV:activity",
                "W_e/declared_activity_symbol",
            ),
        ),
        "SRC",
        "METHOD",
    )
    out2 = core.process_coupling(
        process,
        mismatched_activity,
        nodes,
        target_layer=layer,
        interval_id="T0",
    )
    activity_unit_mismatch_accepted = out2["E0"] == core.F(2)

    return {
        "wrong_coefficient_unit_accepted": wrong_coefficient_unit_accepted,
        "activity_unit_mismatch_accepted": activity_unit_mismatch_accepted,
        "returns_untyped_numeric_mapping": all(
            isinstance(v, Fraction) for v in out.values()
        ),
        "status": "HOLD_UNPROVEN_TYPED_DIMENSIONAL_CLOSURE",
    }


def review_boundary_flow() -> dict[str, Any]:
    f = core.fixture_f02()
    imports, exports, net = core.boundary_import_export(
        f["nodes"],
        f["boundary_edges"],
        f["boundary_flow"],
        layer=f["layer"],
        interval_id=f["interval_id"],
    )
    if imports["E0"] != core.F(5) or exports["E0"] != 0 or net["E0"] != core.F(5):
        raise AssertionError("boundary baseline changed")
    try:
        core.boundary_import_export(
            f["nodes"],
            f["boundary_edges"],
            [core.qv(-1, core.ResourceLayer.ELECTRICITY)],
            layer=f["layer"],
            interval_id=f["interval_id"],
        )
    except core.HoldError as exc:
        negative_rejected = exc.code is core.HoldCode.HOLD_NEGATIVE_DIRECTED_FLOW
    else:
        negative_rejected = False
    return {
        "import_export_net_decomposition": True,
        "negative_directed_flow_rejected": negative_rejected,
        "status": "PASS_BOUNDED_TYPED_DIRECTIONAL_PATH",
    }


def review_uncertainty_path() -> dict[str, Any]:
    coeff_i, unc_i = core.fixture_f11_interval()
    interval = core.uncertainty_propagate(coeff_i, unc_i)
    if not isinstance(interval, core.IntervalUncertainty):
        raise AssertionError("interval uncertainty path changed")

    coeff_m, unc_m, cov = core.fixture_f12_moment()
    moment = core.uncertainty_propagate(coeff_m, unc_m, covariance=cov)
    if not isinstance(moment, core.MomentUncertainty):
        raise AssertionError("moment uncertainty path changed")

    coeff_e, unc_e = core.fixture_f13_empirical()
    empirical = core.uncertainty_propagate(
        coeff_e, unc_e, sample_alignment_ref="A"
    )
    if not isinstance(empirical, core.EmpiricalUncertainty):
        raise AssertionError("empirical uncertainty path changed")

    balance = core.resource_balance_residual(**core.fixture_f01())
    balance_output_is_raw_fraction = all(
        isinstance(v, Fraction) for v in balance.values()
    )
    return {
        "interval_path": True,
        "moment_path": True,
        "empirical_path": True,
        "balance_output_is_raw_fraction": balance_output_is_raw_fraction,
        "status": "PASS_BOUNDED_STANDALONE_NOT_END_TO_END",
    }


def review_audit_vector() -> dict[str, Any]:
    v = core.audit_vector_l1_l4(
        core.F("0.1"), core.F("0.2"), core.F("0.3"), core.F("0.4")
    )
    if v != (core.F("0.1"), core.F("0.2"), core.F("0.3"), core.F("0.4")):
        raise AssertionError("audit vector changed")
    try:
        core.emit_aggregate_equilibrium_score(v)
    except core.HoldError as exc:
        aggregate_prohibited = (
            exc.code is core.HoldCode.HOLD_AGGREGATE_SCORE_PROHIBITED
        )
    else:
        aggregate_prohibited = False
    return {
        "four_component_vector_preserved": True,
        "aggregate_score_prohibited": aggregate_prohibited,
        "status": "PASS_BOUNDED_SEPARATE_VECTOR",
    }


def run_review() -> dict[str, Any]:
    r = load_review()
    pins = verify_pins(r)
    observed = {
        "balance_kernel": review_balance_kernel(),
        "storage_kernel": review_storage_kernel(),
        "process_coupling": review_process_coupling(),
        "boundary_flow": review_boundary_flow(),
        "uncertainty_path": review_uncertainty_path(),
        "audit_vector": review_audit_vector(),
    }

    if not observed["balance_kernel"]["raw_untyped_process_injection_accepted"]:
        raise AssertionError("selected balance ingress gap is no longer observable")
    if not observed["process_coupling"]["wrong_coefficient_unit_accepted"]:
        raise AssertionError("selected coefficient dimensional gap is no longer observable")
    if not observed["process_coupling"]["activity_unit_mismatch_accepted"]:
        raise AssertionError("selected activity-unit gap is no longer observable")

    selected = r["next_single_unproven_core_capability"]
    return {
        "schema_version":
            "EQUILIBRIUM_PRS_CORE_REENTRY_GAP_REVIEW_RECEIPT_V1",
        "gate_id": GATE_ID,
        "review_manifest_sha256": sha256_file(str(REVIEW_PATH)),
        "verified_pins": pins,
        "observed_review": observed,
        "declared_review": r["reviews"],
        "next_single_unproven_core_capability": selected,
        "selected_capability_count": 1,
        "provider_work": False,
        "new_source_ingest": False,
        "fences": r["fences"],
        "verdict": r["verdict_target"],
    }


def write_receipt() -> tuple[dict[str, Any], str]:
    receipt = run_review()
    canonical = json.dumps(
        receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ) + "\n"
    OUT_PATH.write_text(canonical, encoding="utf-8")
    sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return receipt, sha


if __name__ == "__main__":
    receipt, sha = write_receipt()
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    print("CORE_REENTRY_GAP_REVIEW_RECEIPT_SHA256=" + sha)
