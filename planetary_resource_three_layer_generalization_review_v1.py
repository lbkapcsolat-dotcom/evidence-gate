from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import planetary_resource_first_real_source_canary_v1 as water
import planetary_resource_second_real_source_canary_v1 as electricity
import planetary_resource_third_real_source_gas_canary_v1 as gas


GATE_ID = (
    "EQUILIBRIUM__PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__THREE_LAYER_CANARY_GENERALIZATION_REVIEW_V1"
)
REVIEW_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__THREE_LAYER_CANARY_GENERALIZATION_REVIEW.json"
)
OUT_PATH = Path(
    "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1"
    "__THREE_LAYER_CANARY_GENERALIZATION_REVIEW_RECEIPT.json"
)


def sha256_file(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_review() -> dict[str, Any]:
    r = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
    if r["gate_id"] != GATE_ID:
        raise AssertionError("gate id mismatch")
    if r["compared_layers"] != ["FRESHWATER", "ELECTRICITY", "NATURAL_GAS"]:
        raise AssertionError("expected exactly water/electricity/gas review")
    if any(r["fences"].values()):
        raise AssertionError(f"review fence enabled unexpectedly: {r['fences']!r}")
    return r


def canonical_view(receipt: dict[str, Any], layer: str) -> dict[str, Any]:
    a = receipt["empirical_admission_receipt"]
    if a["layer"] != layer:
        raise AssertionError(f"layer mismatch {a['layer']} != {layer}")

    source_key = "source" if "source" in receipt else "measurement_source"
    source = receipt[source_key]
    unit = receipt["unit_transform_receipt"]
    spatial = receipt["spatial_mapping_receipt"]
    temporal = receipt["temporal_alignment_receipt"]
    fresh = receipt["freshness_readback"]
    uncertainty = receipt["uncertainty_declaration"]
    missingness = receipt["missingness_semantics"]

    return {
        "layer": layer,
        "provider": source["provider"],
        "raw_sha256": source["raw_sha256"],
        "raw_byte_length": source["raw_byte_length"],
        "variable_id": a["variable_id"],
        "source_status": missingness["source_status"],
        "admission_decision": a["decision"],
        "canonical_value": {
            "n": a["canonical_value_n"],
            "d": a["canonical_value_d"],
        },
        "canonical_unit": a["canonical_unit"],
        "target_node_id": spatial["target_node_id"],
        "target_node_class": spatial["target_node_class"],
        "spatial_method": spatial["method"],
        "temporal_method": temporal["method"],
        "interpolation_used": bool(temporal["interpolation_used"]),
        "imputation_used": bool(temporal["imputation_used"]),
        "aggregation_performed": bool(temporal.get("aggregation_performed", False)),
        "freshness_age_seconds": fresh["age_seconds"],
        "fresh_at_admission": fresh["fresh_at_admission"],
        "uncertainty_kind": uncertainty["kind"],
        "promotion_to_exact": uncertainty["promotion_to_exact"],
        "value_present": missingness["value_present"],
        "zero_is_missing": missingness["zero_is_missing"],
        "transform_chain": list(a["transform_chain"]),
        "unit_receipt_shape": sorted(unit.keys()),
    }


def assert_shared_schema(view: dict[str, Any]) -> None:
    required = {
        "layer",
        "provider",
        "raw_sha256",
        "raw_byte_length",
        "variable_id",
        "source_status",
        "admission_decision",
        "canonical_value",
        "canonical_unit",
        "target_node_id",
        "target_node_class",
        "spatial_method",
        "temporal_method",
        "interpolation_used",
        "imputation_used",
        "aggregation_performed",
        "freshness_age_seconds",
        "fresh_at_admission",
        "uncertainty_kind",
        "promotion_to_exact",
        "value_present",
        "zero_is_missing",
        "transform_chain",
        "unit_receipt_shape",
    }
    if set(view) != required:
        raise AssertionError(f"normalized schema mismatch: {set(view) ^ required}")
    if len(view["raw_sha256"]) != 64:
        raise AssertionError("raw SHA256 missing")
    if view["admission_decision"] != "ADMIT_OBSERVED":
        raise AssertionError("canary was not observed admission")
    if view["spatial_method"] != "NODE_LOOKUP":
        raise AssertionError("all three canaries should use explicit NODE_LOOKUP")
    if view["temporal_method"] != "EXACT_INTERVAL":
        raise AssertionError("all three canaries should use EXACT_INTERVAL")
    if view["interpolation_used"] or view["imputation_used"] or view["aggregation_performed"]:
        raise AssertionError("silent transform or aggregation present")
    if not view["fresh_at_admission"]:
        raise AssertionError("canary was stale at admission")
    if view["uncertainty_kind"] != "UNKNOWN" or view["promotion_to_exact"]:
        raise AssertionError("uncertainty discipline mismatch")
    if not view["value_present"] or view["zero_is_missing"]:
        raise AssertionError("missingness discipline mismatch")
    if not any(x.startswith("unit:") for x in view["transform_chain"]):
        raise AssertionError("canonical unit transform missing")
    if not any(x.startswith("spatial:") for x in view["transform_chain"]):
        raise AssertionError("spatial transform missing")
    if not any(x.startswith("temporal:") for x in view["transform_chain"]):
        raise AssertionError("temporal transform missing")


def run_review() -> dict[str, Any]:
    r = load_review()

    water_receipt = water.run_canary()
    electricity_receipt = electricity.run_canary()
    gas_receipt = gas.run_canary()

    views = {
        "FRESHWATER": canonical_view(water_receipt, "FRESHWATER"),
        "ELECTRICITY": canonical_view(electricity_receipt, "ELECTRICITY"),
        "NATURAL_GAS": canonical_view(gas_receipt, "NATURAL_GAS"),
    }
    for view in views.values():
        assert_shared_schema(view)

    # Frozen source bytes and empirical contract must remain unchanged.
    pins = r["predecessor"]
    expected = {
        "empirical_contract_sha256": (
            "EQUILIBRIUM_PLANETARY_RESOURCE_SYSTEMS_CORE_V1__EMPIRICAL_DATA_CONTRACT.json",
            pins["empirical_contract_sha256"],
        ),
        "empirical_validator_sha256": (
            "planetary_resource_empirical_admission_v1.py",
            pins["empirical_validator_sha256"],
        ),
        "water_raw_sha256": (
            "sources/environment_agency/1100TH_flow_mean_15min_2026-10-01T21-30Z.json",
            "c180db17bc02d371f1eebb4667695b715f0ce2f9c2f97bab6893b77f87c97c29",
        ),
        "electricity_raw_sha256": (
            "sources/elexon/INDO_2026-10-01T22-00Z.json",
            "831ed964ef11527f0d8db767665289b59f5ef7b32fac02cd7667ad4b949a7242",
        ),
        "gas_raw_sha256": (
            "sources/entsog/DE-TSO-0005_ITP-00188_entry_physical_flow_2026-10-01T21-22Z.html",
            "a7f15400b518ec51ac0f6a97696bd7cd261e64730d1a348dc1a2ad0be0956928",
        ),
    }
    actual_hashes: dict[str, str] = {}
    for name, (path, want) in expected.items():
        got = sha256_file(path)
        if got != want:
            raise AssertionError(f"{name} changed: {got} != {want}")
        actual_hashes[name] = got

    # Shared adapter: source-specific parsing and semantic/unit evidence sit
    # outside the frozen empirical admission validator. Core domain arithmetic
    # is never reimplemented per provider.
    if r["generalization_findings"]["domain_math_reimplementation_per_source_required"]:
        raise AssertionError("review illegally requires per-source domain math")
    if r["generalization_findings"]["provider_specific_physics_engine_required"]:
        raise AssertionError("review illegally requires provider-specific physics engine")

    gas_chain = set(views["NATURAL_GAS"]["transform_chain"])
    if "energy_basis:GCV" not in gas_chain:
        raise AssertionError("gas layer-specific energy basis exception missing")
    if "terminology:GCV->HHV" not in gas_chain:
        raise AssertionError("gas GCV/HHV terminology mapping missing")

    decision = r["crude_oil_decision"]
    expected_decision = {
        "adapter_generalization_requires_oil_canary": False,
        "four_layer_real_world_coverage_requires_oil_canary": True,
        "before_any_crude_oil_source_admission": True,
        "before_claiming_all_four_v1_layers_real_world_tested": True,
        "recommended_now": False,
        "decision": "DEFER_UNTIL_CRUDE_OIL_ADMISSION_OR_FOUR_LAYER_COVERAGE_CLAIM",
    }
    for key, value in expected_decision.items():
        if decision[key] != value:
            raise AssertionError(f"crude-oil decision mismatch for {key}")

    receipt = {
        "schema_version": "EQUILIBRIUM_PRS_THREE_LAYER_GENERALIZATION_REVIEW_RECEIPT_V1",
        "gate_id": GATE_ID,
        "review_sha256": sha256_file(str(REVIEW_PATH)),
        "preserved_hashes": actual_hashes,
        "canary_views": views,
        "shared_adapter_stage_count": len(r["shared_adapter_schema"]["stages"]),
        "shared_adapter_stages": r["shared_adapter_schema"]["stages"],
        "layer_specific_exceptions": r["layer_specific_exceptions"],
        "generalization_findings": r["generalization_findings"],
        "crude_oil_decision": decision,
        "fences": r["fences"],
        "verdict": r["verdict"],
    }
    return receipt


def write_receipt() -> tuple[dict[str, Any], str]:
    receipt = run_review()
    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    OUT_PATH.write_text(canonical, encoding="utf-8")
    sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return receipt, sha


if __name__ == "__main__":
    receipt, sha = write_receipt()
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    print("THREE_LAYER_GENERALIZATION_REVIEW_RECEIPT_SHA256=" + sha)
