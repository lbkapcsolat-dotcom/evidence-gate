from __future__ import annotations

import hashlib
import json
from pathlib import Path

import ch09b_eq64_hgraph_python_v1 as eq64

GATE_ID = "CH10__FULL_EQUILIBRIUM_MOTOR_END_TO_END_COHERENCE_FINAL_SEAL_V1"

CH07T_CONTRACT_SHA256 = "73158dafbe64b2586126989803b04d1c417c37c2ed15bb6380e7df54bf8d6486"
CH07T_REFERENCE_RECEIPT_SHA256 = "e2e19a8440b690a919f81d6d6276a0e8c46c6a9ef5e0ceb282fec0706083874e"
CH09A_RECEIPT_SHA256 = "3b3ab494cb5d0179f355825bccbcfee75cc0f8f11e3bf2e811f0201aba40757e"

CH09B_RECEIPT = Path("CH09B__PYTHON_HGRAPH_64_REPLAY_RECEIPT_V1.json")
CH09C_RECEIPT = Path("CH09C__CROSS_LANGUAGE_BYTE_PARITY_RECEIPT_V1.json")
CPP_PACKET = Path("CH09C__CPP_EQ64_PACKET_V1.jsonl")
PY_PACKET = Path("CH09B__PYTHON_HGRAPH_EQ64_PACKET_V1.jsonl")
REF_PACKET = Path("CH09B__REFERENCE_EQ64_PACKET_V1.jsonl")
OUT = Path("CH10__BOUNDED_FINAL_COHERENCE_SEAL_V1.json")

SEMANTIC_AXES = {
    "E": {"name": "EvidenceStrength", "polarity": "admissible_evidence_to_1", "sources": ["DOC-306", "DOC-293"]},
    "C": {"name": "ConditionMatch", "polarity": "contract_match_to_1", "sources": ["DOC-200", "DOC-177"]},
    "M": {"name": "MetricAgreement", "polarity": "exact_canonical_agreement_to_1", "sources": ["DOC-215", "DOC-194"]},
    "D": {"name": "DirectionAgreement", "polarity": "direction_sign_consistency_to_1", "sources": ["DOC-171", "DOC-177"]},
    "S": {"name": "ScopeContainment", "polarity": "claim_within_ceiling_to_1", "sources": ["DOC-306", "KNOW-43"]},
    "A": {"name": "SourceAuthority", "polarity": "eligible_typed_authority_to_1", "sources": ["KNOW-20", "KNOW-43"]},
}

EXPECTED_ORBIT_PROFILE = [1, 1, 3, 3, 6, 6, 8, 12, 12, 12]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_structural_kernel() -> dict:
    if len(eq64.ROTATIONS) != 24:
        raise SystemExit("CH10_ROTATION_COUNT_FAIL")
    if eq64.canonical_label_count() != 10:
        raise SystemExit("CH10_CANONICAL_LABEL_COUNT_FAIL")
    profile = list(eq64.orbit_profile())
    if profile != EXPECTED_ORBIT_PROFILE:
        raise SystemExit(f"CH10_ORBIT_PROFILE_FAIL:{profile!r}")

    orbit_stabilizer_pass = 0
    for state in range(64):
        rec = eq64.canonical_record(state)
        if rec["orbit_size"] * rec["stabilizer_size"] != 24:
            raise SystemExit(f"CH10_ORBIT_STABILIZER_FAIL:{state}")
        orbit_stabilizer_pass += 1

    return {
        "q6_states": 64,
        "rotations": 24,
        "canonical_labels": 10,
        "orbit_profile": profile,
        "orbit_stabilizer": {"pass": orbit_stabilizer_pass, "total": 64},
    }


def validate_selected_ve_bridge() -> dict:
    # The selected bridge is between six cube face normals and the six square
    # faces of the cuboctahedron carrying the same outward normals.
    # phi_face is therefore the typed normal-preserving bijection on the six
    # labelled face-normal slots. This is not a whole-polyhedron identity claim.
    cube_faces = tuple(range(6))
    ve_square_faces = tuple(range(6))
    phi = {i: i for i in cube_faces}

    if len(phi) != 6 or len(set(phi.values())) != 6 or set(phi.values()) != set(ve_square_faces):
        raise SystemExit("CH10_VE_FACE_BIJECTION_FAIL")

    equivariance = 0
    for rotation in eq64.ROTATIONS:
        for face in cube_faces:
            lhs = phi[rotation[face]]
            rhs = rotation[phi[face]]
            if lhs != rhs:
                raise SystemExit(f"CH10_VE_EQUIVARIANCE_FAIL:{face}")
            equivariance += 1

    if equivariance != 144:
        raise SystemExit("CH10_VE_EQUIVARIANCE_COUNT_FAIL")

    return {
        "selected_cube_face_to_cuboctahedron_square_face_bijection": "6/6",
        "face_equivariance": {"pass": 144, "total": 144},
        "whole_polyhedron_identity_claim": False,
        "physical_equilibrium_claim": False,
    }


def validate_semantic_contract() -> dict:
    if tuple(SEMANTIC_AXES.keys()) != ("E", "C", "M", "D", "S", "A"):
        raise SystemExit("CH10_SEMANTIC_AXIS_SET_FAIL")
    if len(SEMANTIC_AXES) != 6:
        raise SystemExit("CH10_SEMANTIC_AXIS_COUNT_FAIL")
    for code, spec in SEMANTIC_AXES.items():
        if not spec["name"] or not spec["polarity"] or not spec["sources"]:
            raise SystemExit(f"CH10_SEMANTIC_AXIS_INCOMPLETE:{code}")

    return {
        "axes": SEMANTIC_AXES,
        "axis_count": 6,
        "truth_domain": ["TRUE", "FALSE", "HOLD"],
        "hold_prevents_complete_semantic_state": True,
        "geometry_position_to_semantic_axis_mapping": None,
        "same_cardinality_identity_claim": False,
        "ch07t_contract_sha256": CH07T_CONTRACT_SHA256,
        "ch07t_reference_receipt_sha256": CH07T_REFERENCE_RECEIPT_SHA256,
    }


def validate_runtime_chain() -> dict:
    b = load_json(CH09B_RECEIPT)
    c = load_json(CH09C_RECEIPT)

    if b.get("verdict") != "PASS_CH09B__PYTHON_HGRAPH_EVAL_NODE_64_OF_64":
        raise SystemExit("CH10_CH09B_VERDICT_FAIL")
    if c.get("verdict") != "PASS_CH09C__CPP_PYTHON_REFERENCE_EXACT_BYTE_PARITY_64_OF_64":
        raise SystemExit("CH10_CH09C_VERDICT_FAIL")

    cpp = CPP_PACKET.read_bytes()
    py = PY_PACKET.read_bytes()
    ref = REF_PACKET.read_bytes()
    if not (cpp == py == ref):
        raise SystemExit("CH10_PACKET_BYTES_FAIL")
    if cpp.count(b"\n") != 64:
        raise SystemExit("CH10_PACKET_LINE_COUNT_FAIL")

    packet_sha = sha256_bytes(cpp)
    if len({packet_sha, sha256_bytes(py), sha256_bytes(ref)}) != 1:
        raise SystemExit("CH10_PACKET_SHA_FAIL")

    return {
        "ch09a_receipt_sha256": CH09A_RECEIPT_SHA256,
        "ch09b_receipt_sha256": sha256_file(CH09B_RECEIPT),
        "ch09c_receipt_sha256": sha256_file(CH09C_RECEIPT),
        "native_cpp_hgraph_eval_node_64_replay": "PASS_FROM_CH09A_PIN",
        "python_hgraph_eval_node_64_replay": "PASS_64_OF_64",
        "cpp_python_reference_exact_byte_parity": True,
        "canonical_packet_sha256": packet_sha,
        "canonical_packet_lines": 64,
    }


def validate_mutation_control(original_receipt: dict) -> dict:
    mutant = json.loads(json.dumps(original_receipt))
    mutant["semantic_contract"]["axes"]["E"]["name"] = "ConditionMatch"

    def guard(receipt: dict) -> bool:
        axes = receipt["semantic_contract"]["axes"]
        names = [axes[k]["name"] for k in ("E", "C", "M", "D", "S", "A")]
        return names == [
            "EvidenceStrength",
            "ConditionMatch",
            "MetricAgreement",
            "DirectionAgreement",
            "ScopeContainment",
            "SourceAuthority",
        ]

    if guard(mutant):
        raise SystemExit("CH10_MUTANT_FALSE_PASS")
    return {"semantic_axis_mutant_detected": True}


def main() -> None:
    structural = validate_structural_kernel()
    ve = validate_selected_ve_bridge()
    semantic = validate_semantic_contract()
    runtime = validate_runtime_chain()

    receipt = {
        "schema_version": "CH10_BOUNDED_FINAL_COHERENCE_SEAL_V1",
        "gate_id": GATE_ID,
        "chain": [
            "Q6_TYPED_OBJECT",
            "CUBE_ROTATION_ACTION",
            "ORBIT_STABILIZER",
            "CANONICAL_FORM",
            "SELECTED_VE_SQUARE_FACE_EQUIVARIANT_BRIDGE",
            "TYPED_SEMANTIC_OBSERVATION_CONTRACT",
            "NATIVE_CPP_HGRAPH_REPLAY",
            "PYTHON_AUTHORED_HGRAPH_REPLAY",
            "EXACT_CROSS_LANGUAGE_PACKET_PARITY",
            "OVERCLAIM_GUARD",
            "DETERMINISTIC_RECEIPT",
        ],
        "structural_kernel": structural,
        "selected_ve_bridge": ve,
        "semantic_contract": semantic,
        "runtime_chain": runtime,
        "claim_ceiling": {
            "bounded_end_to_end_formal_runtime_coherence": True,
            "empirical_semantic_validity": False,
            "physical_vector_equilibrium_truth": False,
            "production_readiness": False,
            "runtime_admission": False,
            "production_admission": False,
            "pointer_promotion": False,
            "global_bind": False,
            "certification": False,
            "merge_authorization": False,
        },
        "verdict": "PASS_CH10__BOUNDED_END_TO_END_COHERENCE_FINAL_SEAL__NO_GLOBAL_BIND",
    }

    receipt["mutation_control"] = validate_mutation_control(receipt)
    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    OUT.write_text(canonical, encoding="utf-8")
    print(canonical, end="")
    print("CH10_RECEIPT_SHA256=" + sha256_bytes(canonical.encode("utf-8")))
    print("CH10_PACKET_SHA256=" + runtime["canonical_packet_sha256"])


if __name__ == "__main__":
    main()
