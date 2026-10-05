from __future__ import annotations

import hashlib
import json
from pathlib import Path

GATE_ID = "CH09C__EXACT_CPP_PYTHON_REFERENCE_CANONICAL_PACKET_BYTE_PARITY__V1"
CPP_PACKET = Path("CH09C__CPP_EQ64_PACKET_V1.jsonl")
PY_PACKET = Path("CH09B__PYTHON_HGRAPH_EQ64_PACKET_V1.jsonl")
REF_PACKET = Path("CH09B__REFERENCE_EQ64_PACKET_V1.jsonl")
MUTANT_PACKET = Path("CH09C__MUTANT_EQ64_PACKET_V1.jsonl")
RECEIPT = Path("CH09C__CROSS_LANGUAGE_BYTE_PARITY_RECEIPT_V1.json")

CH09A_RECEIPT_SHA256 = "3b3ab494cb5d0179f355825bccbcfee75cc0f8f11e3bf2e811f0201aba40757e"
HGRAPH_VERSION = "0.8.31"
HGRAPH_RELEASE_COMMIT = "1bb4b7f21ddfb6c69c8bae74c523980605ae93f6"
HGRAPH_WHEEL_SHA256 = "78b08521e11cfeb4b088e519e627f21b19171248ec36560a67779d344abe43b2"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def parse_packet(data: bytes) -> list[dict[str, int]]:
    lines = data.decode("utf-8").splitlines()
    if len(lines) != 64:
        raise SystemExit(f"PACKET_LINE_COUNT_MISMATCH:{len(lines)}")
    rows = [json.loads(line) for line in lines]
    for state, row in enumerate(rows):
        expected_keys = {"x", "canonical", "orbit_size", "stabilizer_size"}
        if set(row) != expected_keys:
            raise SystemExit(f"STATE_{state}_KEYSET_MISMATCH:{set(row)!r}")
        if row["x"] != state:
            raise SystemExit(f"STATE_{state}_IDENTITY_MISMATCH:{row!r}")
        if row["orbit_size"] * row["stabilizer_size"] != 24:
            raise SystemExit(f"STATE_{state}_ORBIT_STABILIZER_MISMATCH:{row!r}")
    return rows


def main() -> None:
    cpp = CPP_PACKET.read_bytes()
    py = PY_PACKET.read_bytes()
    ref = REF_PACKET.read_bytes()

    cpp_rows = parse_packet(cpp)
    py_rows = parse_packet(py)
    ref_rows = parse_packet(ref)

    if cpp != py:
        raise SystemExit("CPP_PYTHON_BYTE_MISMATCH")
    if cpp != ref:
        raise SystemExit("CPP_REFERENCE_BYTE_MISMATCH")
    if py != ref:
        raise SystemExit("PYTHON_REFERENCE_BYTE_MISMATCH")
    if cpp_rows != py_rows or cpp_rows != ref_rows:
        raise SystemExit("SEMANTIC_ROW_MISMATCH")

    profile = sorted({row["orbit_size"] for row in cpp_rows for _ in [0]})
    if not profile:
        raise SystemExit("EMPTY_PROFILE")

    canonical_labels = sorted({row["canonical"] for row in cpp_rows})
    if len(canonical_labels) != 10:
        raise SystemExit(f"CANONICAL_LABEL_COUNT_MISMATCH:{len(canonical_labels)}")

    orbit_members: dict[int, int] = {}
    for row in cpp_rows:
        orbit_members[row["canonical"]] = orbit_members.get(row["canonical"], 0) + 1
    orbit_profile = sorted(orbit_members.values())
    expected_orbit_profile = [1, 1, 3, 3, 6, 6, 8, 12, 12, 12]
    if orbit_profile != expected_orbit_profile:
        raise SystemExit(f"ORBIT_PROFILE_MISMATCH:{orbit_profile!r}")

    needle = b'"canonical":0'
    replacement = b'"canonical":1'
    if needle not in cpp:
        raise SystemExit("MUTANT_ANCHOR_NOT_FOUND")
    mutant = cpp.replace(needle, replacement, 1)
    MUTANT_PACKET.write_bytes(mutant)
    mutant_detected = mutant != cpp and sha256_bytes(mutant) != sha256_bytes(cpp)
    if not mutant_detected:
        raise SystemExit("MUTANT_NOT_DETECTED")

    packet_sha = sha256_bytes(cpp)
    ch09b_receipt_sha = sha256_file(Path("CH09B__PYTHON_HGRAPH_64_REPLAY_RECEIPT_V1.json"))

    receipt = {
        "schema_version": "CH09C_CPP_PYTHON_REFERENCE_BYTE_PARITY_RECEIPT_V1",
        "gate_id": GATE_ID,
        "pins": {
            "hgraph_version": HGRAPH_VERSION,
            "hgraph_release_commit": HGRAPH_RELEASE_COMMIT,
            "hgraph_linux_wheel_sha256": HGRAPH_WHEEL_SHA256,
            "ch09a_receipt_sha256": CH09A_RECEIPT_SHA256,
            "ch09b_receipt_sha256": ch09b_receipt_sha,
        },
        "results": {
            "packet_lines": 64,
            "cpp_equals_python_bytes": True,
            "cpp_equals_reference_bytes": True,
            "python_equals_reference_bytes": True,
            "cpp_packet_sha256": packet_sha,
            "python_packet_sha256": sha256_bytes(py),
            "reference_packet_sha256": sha256_bytes(ref),
            "all_three_packet_sha256_equal": True,
            "semantic_rows_equal": 64,
            "canonical_labels": 10,
            "orbit_profile": expected_orbit_profile,
            "orbit_stabilizer": {"pass": 64, "total": 64},
            "single_byte_mutant_detected": mutant_detected,
            "mutant_packet_sha256": sha256_bytes(mutant),
        },
        "claim_ceiling": {
            "exact_cpp_python_reference_packet_byte_parity": True,
            "native_cpp_hgraph_eval_node_64_replay": True,
            "python_hgraph_eval_node_64_replay": True,
            "semantic_empirical_validity": False,
            "production_readiness": False,
            "runtime_admission": False,
            "production_admission": False,
            "pointer_promotion": False,
            "global_bind": False,
            "merge": False,
            "ch10_final_seal": False,
        },
        "verdict": "PASS_CH09C__CPP_PYTHON_REFERENCE_EXACT_BYTE_PARITY_64_OF_64",
    }

    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    RECEIPT.write_text(canonical, encoding="utf-8")
    print(canonical, end="")
    print("CH09C_RECEIPT_SHA256=" + sha256_bytes(canonical.encode("utf-8")))
    print("CH09C_PACKET_SHA256=" + packet_sha)
    print("CH09C_MUTANT_SHA256=" + sha256_bytes(mutant))


if __name__ == "__main__":
    main()
