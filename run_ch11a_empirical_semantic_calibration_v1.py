from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
from typing import Any

import planetary_resource_empirical_admission_v1 as admission
import planetary_resource_first_real_source_canary_v1 as water
import planetary_resource_second_real_source_canary_v1 as electricity
import planetary_resource_third_real_source_gas_canary_v1 as gas
import planetary_resource_generic_source_adapter_gate_v1 as generic_gate
import planetary_resource_generic_source_adapter_conformance_v1 as conformance
import planetary_resource_generic_source_bindings_v1 as bindings
import planetary_resource_integration_readiness_freeze_v1 as integration_freeze

GATE_ID = "CH11A__EMPIRICAL_SEMANTIC_CALIBRATION_ON_REAL_SOURCE_CORPUS_V1"
CORPUS_PATH = Path("CH11A__SEMANTIC_CALIBRATION_CORPUS_V1.json")
OUT_PATH = Path("CH11A__EMPIRICAL_SEMANTIC_CALIBRATION_RECEIPT_V1.json")

CH07T_CONTRACT_SHA256 = "73158dafbe64b2586126989803b04d1c417c37c2ed15bb6380e7df54bf8d6486"
CH07T_REFERENCE_RECEIPT_SHA256 = "e2e19a8440b690a919f81d6d6276a0e8c46c6a9ef5e0ceb282fec0706083874e"
CH10_RECEIPT_SHA256 = "6e14308dbe21eacc0cda91497b564255834065875b46f0d475bdb2a5e45e4be3"
SUT_FREEZE_RECEIPT_SHA256 = "619e34873fc12d88cb102d727a28256c0fd17f7fc4a4007413ec5c45522a7d70"

RAW_PATHS = {
    "water": Path("sources/environment_agency/1100TH_flow_mean_15min_2026-10-01T21-30Z.json"),
    "electricity": Path("sources/elexon/INDO_2026-10-01T22-00Z.json"),
    "natural_gas": Path("sources/entsog/DE-TSO-0005_ITP-00188_entry_physical_flow_2026-10-01T21-22Z.html"),
}
RAW_SHA256 = {
    "water": "c180db17bc02d371f1eebb4667695b715f0ce2f9c2f97bab6893b77f87c97c29",
    "electricity": "831ed964ef11527f0d8db767665289b59f5ef7b32fac02cd7667ad4b949a7242",
    "natural_gas": "a7f15400b518ec51ac0f6a97696bd7cd261e64730d1a348dc1a2ad0be0956928",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_sha256(payload: Any) -> str:
    # Match the frozen project receipt convention exactly: canonical JSON + LF.
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    return sha256_bytes(body.encode("utf-8"))


def load_corpus() -> dict[str, Any]:
    corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    if corpus["schema_version"] != "CH11A_SEMANTIC_CALIBRATION_CORPUS_V1":
        raise AssertionError("corpus schema changed")
    if corpus["case_count"] != 36 or len(corpus["cases"]) != 36:
        raise AssertionError("calibration corpus must contain exactly 36 cases")
    if corpus["axes"] != ["E", "C", "M", "D", "S", "A"]:
        raise AssertionError("axis order changed")
    counts = Counter(row["axis"] for row in corpus["cases"])
    if counts != Counter({"E": 6, "C": 6, "M": 6, "D": 6, "S": 6, "A": 6}):
        raise AssertionError(f"axis case counts changed: {counts!r}")
    return corpus


def eval_evidence_strength(f: dict[str, Any]) -> str:
    required = ("provenance_complete", "raw_sha_verified", "fresh", "effective_domains", "required_domains")
    if any(k not in f for k in required):
        return "HOLD"
    if not f["provenance_complete"] or not f["raw_sha_verified"] or not f["fresh"]:
        return "HOLD"
    if f["effective_domains"] < f["required_domains"]:
        return "FALSE"
    return "TRUE"


def eval_condition_match(f: dict[str, Any]) -> str:
    if "metadata_complete" not in f or "explicit_mismatch" not in f:
        return "HOLD"
    if not f["metadata_complete"]:
        return "HOLD"
    if f["explicit_mismatch"]:
        return "FALSE"
    return "TRUE"


def eval_metric_agreement(f: dict[str, Any]) -> str:
    if not f.get("comparator") or not f.get("values_available", False):
        return "HOLD"
    if f["comparator"] != "EXACT_CANONICAL_EQUALITY":
        return "HOLD"
    return "TRUE" if f.get("exact_equal") is True else "FALSE"


def eval_direction_agreement(f: dict[str, Any]) -> str:
    if not f.get("direction_semantics_declared", False):
        return "HOLD"
    if not f.get("relation_known", False):
        return "HOLD"
    return "TRUE" if f.get("relation_consistent") is True else "FALSE"


def eval_scope_containment(f: dict[str, Any]) -> str:
    if not f.get("requested_scope_known", False) or not f.get("claim_ceiling_known", False):
        return "HOLD"
    return "TRUE" if f.get("contained") is True else "FALSE"


def eval_source_authority(f: dict[str, Any], allowlist: set[tuple[str, str]]) -> str:
    if not f.get("authority_proof_present", False) or not f.get("unique_source", False):
        return "HOLD"
    provider = f.get("provider", "")
    role = f.get("role", "")
    if not provider or not role:
        return "HOLD"
    eligible = f.get("eligible")
    if eligible is False:
        return "FALSE"
    if eligible is not True:
        return "HOLD"
    if (provider, role) not in allowlist:
        return "FALSE"
    if not f.get("evidence_backed", False):
        return "HOLD"
    return "TRUE"


def evaluate(axis: str, features: dict[str, Any], allowlist: set[tuple[str, str]]) -> str:
    if axis == "E":
        return eval_evidence_strength(features)
    if axis == "C":
        return eval_condition_match(features)
    if axis == "M":
        return eval_metric_agreement(features)
    if axis == "D":
        return eval_direction_agreement(features)
    if axis == "S":
        return eval_scope_containment(features)
    if axis == "A":
        return eval_source_authority(features, allowlist)
    raise AssertionError(f"unknown axis {axis}")


def verify_raw_sources() -> dict[str, str]:
    out: dict[str, str] = {}
    for name, path in RAW_PATHS.items():
        got = sha256_file(path)
        expected = RAW_SHA256[name]
        if got != expected:
            raise AssertionError(f"{name} raw source changed: {got} != {expected}")
        out[name] = got
    return out


def verify_live_sut_evidence() -> dict[str, Any]:
    # Re-run the frozen integration-readiness verifier. This internally replays
    # the core, successor pins, adapter subsystem and all three real source canaries.
    freeze = integration_freeze.run_freeze()
    freeze_sha = canonical_sha256(freeze)
    if freeze_sha != SUT_FREEZE_RECEIPT_SHA256:
        raise AssertionError(f"SUT integration freeze receipt changed: {freeze_sha}")

    canaries = {
        "water": water.run_canary(),
        "electricity": electricity.run_canary(),
        "gas": gas.run_canary(),
    }
    generic = generic_gate.run_gate()
    if generic["three_of_three_equal"] is not True:
        raise AssertionError("generic adapter receipt equality is not 3/3")

    conformance_rows = conformance.run_rejection_matrix()
    conformance_map = {row["id"]: row["observed"] for row in conformance_rows}
    required_conformance = {
        "R01": "HOLD_BINDING_REQUIRED_FIELD_MISSING",
        "R04": "HOLD_BINDING_RAW_SHA_MISMATCH",
    }
    for case_id, expected in required_conformance.items():
        if conformance_map.get(case_id) != expected:
            raise AssertionError(f"conformance oracle changed: {case_id}")

    admission_rows = admission.run_admission_matrix()
    admission_map = {row.id: row.observed for row in admission_rows}
    required_admission = {
        "A09": "HOLD_LAYER_MISMATCH",
        "A17": "HOLD_TEMPORAL_ALIGNMENT_UNDECLARED",
        "A23": "HOLD_STALE_INPUT",
        "A30": "HOLD_OUT_OF_SCOPE_INPUT",
        "A31": "HOLD_SIGN_SEMANTICS_UNDECLARED",
    }
    for case_id, expected in required_admission.items():
        if admission_map.get(case_id) != expected:
            raise AssertionError(f"admission oracle changed: {case_id}")

    specs = {
        "water": bindings.water_binding(),
        "electricity": bindings.electricity_binding(),
        "gas": bindings.gas_binding(),
    }
    provider_role = {
        "water": ("Environment Agency", "freshwater.internal_flow_rate"),
        "electricity": ("Elexon Insights Solution", "electricity.consumption_rate"),
        "gas": ("ENTSOG Transparency Platform", "natural_gas.import_rate"),
    }
    for name, (spec, _) in specs.items():
        if (spec.provider, spec.variable_id) != provider_role[name]:
            raise AssertionError(f"provider/role identity changed for {name}")
        if spec.sign_semantics_declared is not True:
            raise AssertionError(f"sign semantics lost for {name}")

    gas_receipt = canaries["gas"]
    if gas_receipt["measurement_source"]["direction"] != "entry":
        raise AssertionError("gas direction changed")

    # Executable metric mutation: field-for-field equality must notice change.
    water_existing = canaries["water"]["empirical_admission_receipt"]
    water_mutant = dict(water_existing)
    water_mutant["canonical_value_n"] = int(water_mutant["canonical_value_n"]) + 1
    if water_mutant == water_existing:
        raise AssertionError("metric mutation escaped equality")

    return {
        "integration_freeze_receipt_sha256": freeze_sha,
        "canary_receipt_sha256": {
            "water": canonical_sha256(canaries["water"]),
            "electricity": canonical_sha256(canaries["electricity"]),
            "gas": canonical_sha256(canaries["gas"]),
        },
        "generic_three_of_three_equal": True,
        "conformance_oracles": required_conformance,
        "admission_oracles": required_admission,
        "metric_mutation_detected": True,
        "gas_direction": "entry",
    }


def run_calibration() -> dict[str, Any]:
    corpus = load_corpus()
    raw = verify_raw_sources()
    sut = verify_live_sut_evidence()

    allowlist = {
        (row["provider"], row["role"])
        for row in corpus["authority_allowlist"]
    }
    if len(allowlist) != 3:
        raise AssertionError("authority allowlist must contain exactly three bindings")

    rows: list[dict[str, Any]] = []
    by_axis: dict[str, Counter[str]] = defaultdict(Counter)
    false_pass = 0

    for case in corpus["cases"]:
        # Important: the evaluator sees only axis + features + frozen allowlist.
        observed = evaluate(case["axis"], dict(case["features"]), allowlist)
        expected = case["expected"]
        passed = observed == expected
        if expected != "TRUE" and observed == "TRUE":
            false_pass += 1
        by_axis[case["axis"]]["count"] += 1
        by_axis[case["axis"]]["pass"] += int(passed)
        rows.append({
            "id": case["id"],
            "axis": case["axis"],
            "source_ref": case["source_ref"],
            "evidence_class": case["evidence_class"],
            "expected": expected,
            "observed": observed,
            "passed": passed,
        })

    passed = sum(1 for row in rows if row["passed"])
    if passed != 36:
        first = next(row for row in rows if not row["passed"])
        raise AssertionError(f"calibration mismatch: {first}")
    if false_pass != 0:
        raise AssertionError(f"false PASS count {false_pass}")

    axis_summary = {
        axis: {"pass": by_axis[axis]["pass"], "count": by_axis[axis]["count"]}
        for axis in ["E", "C", "M", "D", "S", "A"]
    }
    if any(v != {"pass": 6, "count": 6} for v in axis_summary.values()):
        raise AssertionError(f"axis calibration incomplete: {axis_summary!r}")

    receipt = {
        "schema_version": "CH11A_EMPIRICAL_SEMANTIC_CALIBRATION_RECEIPT_V1",
        "gate_id": GATE_ID,
        "predecessor_pins": {
            "ch07t_contract_sha256": CH07T_CONTRACT_SHA256,
            "ch07t_reference_receipt_sha256": CH07T_REFERENCE_RECEIPT_SHA256,
            "ch10_receipt_sha256": CH10_RECEIPT_SHA256,
            "sut_integration_freeze_receipt_sha256": SUT_FREEZE_RECEIPT_SHA256,
        },
        "corpus_sha256": sha256_file(CORPUS_PATH),
        "raw_source_sha256": raw,
        "live_sut_revalidation": sut,
        "calibration": {
            "pass": passed,
            "count": 36,
            "false_pass_count": false_pass,
            "axis_summary": axis_summary,
            "rows": rows,
        },
        "authority_allowlist": [
            {"provider": p, "role": r}
            for p, r in sorted(allowlist)
        ],
        "claim_ceiling": {
            "frozen_corpus_semantic_calibration": True,
            "population_level_empirical_validity": False,
            "arbitrary_provider_authority": False,
            "live_network_runtime_admission": False,
            "production_readiness": False,
            "production_admission": False,
            "pointer_promotion": False,
            "global_bind": False,
            "merge_authorization": False,
        },
        "verdict": "PASS_CH11A__EMPIRICAL_SEMANTIC_CALIBRATION_36_OF_36__ZERO_FALSE_PASS__FROZEN_CORPUS_ONLY",
    }
    return receipt


def write_receipt() -> tuple[dict[str, Any], str]:
    receipt = run_calibration()
    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    OUT_PATH.write_text(canonical, encoding="utf-8")
    return receipt, sha256_bytes(canonical.encode("utf-8"))


if __name__ == "__main__":
    receipt, sha = write_receipt()
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    print("CH11A_RECEIPT_SHA256=" + sha)
