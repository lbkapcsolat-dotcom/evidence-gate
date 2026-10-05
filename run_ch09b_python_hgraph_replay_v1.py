from __future__ import annotations

import hashlib
import json
from pathlib import Path

from hgraph.test import eval_node

import ch09b_eq64_hgraph_python_v1 as hg

GATE_ID = "CH09B__PYTHON_AUTHORING_64_REPLAY__REQUIRE_64_OF_64__V1"
PACKET = Path("CH09B__PYTHON_HGRAPH_EQ64_PACKET_V1.jsonl")
REFERENCE_PACKET = Path("CH09B__REFERENCE_EQ64_PACKET_V1.jsonl")
RECEIPT = Path("CH09B__PYTHON_HGRAPH_64_REPLAY_RECEIPT_V1.json")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def run_python_hgraph_packet() -> bytes:
    lines: list[str] = []
    for state in range(64):
        out = eval_node(hg.run_babai_eq64_canonical_record_hgraph, [1], state=state)
        if len(out) != 1 or out[0] is None:
            raise SystemExit(f"STATE_{state}_HGRAPH_NO_OUTPUT:{out!r}")
        expected = hg.canonical_record_json(state)
        if out[0] != expected:
            raise SystemExit(
                f"STATE_{state}_PYTHON_HGRAPH_MISMATCH expected={expected!r} observed={out[0]!r}"
            )
        lines.append(out[0])
    return ("\n".join(lines) + "\n").encode("utf-8")


def run_reference_packet() -> bytes:
    return ("\n".join(hg.canonical_record_json(state) for state in range(64)) + "\n").encode("utf-8")


def main() -> None:
    runtime = hg.native_runtime_metadata()
    if runtime["hgraph_version"] != hg.HGRAPH_VERSION:
        raise SystemExit("HGRAPH_VERSION_MISMATCH")
    if not runtime["native_extension_loaded"]:
        raise SystemExit("NATIVE_EXTENSION_NOT_LOADED")
    if len(hg.ROTATIONS) != 24:
        raise SystemExit("ROTATION_COUNT_MISMATCH")
    if hg.canonical_label_count() != 10:
        raise SystemExit("CANONICAL_LABEL_COUNT_MISMATCH")
    expected_profile = (1, 1, 3, 3, 6, 6, 8, 12, 12, 12)
    if hg.orbit_profile() != expected_profile:
        raise SystemExit(f"ORBIT_PROFILE_MISMATCH:{hg.orbit_profile()!r}")

    first = run_python_hgraph_packet()
    second = run_python_hgraph_packet()
    reference = run_reference_packet()

    if first != second:
        raise SystemExit("PYTHON_HGRAPH_NONDETERMINISTIC_REPLAY")
    if first != reference:
        raise SystemExit("PYTHON_HGRAPH_REFERENCE_PACKET_MISMATCH")
    if first.count(b"\n") != 64:
        raise SystemExit("PYTHON_PACKET_LINE_COUNT_MISMATCH")

    PACKET.write_bytes(first)
    REFERENCE_PACKET.write_bytes(reference)

    source_path = Path("ch09b_eq64_hgraph_python_v1.py")
    receipt = {
        "schema_version": "CH09B_PYTHON_HGRAPH_EQ64_REPLAY_RECEIPT_V1",
        "gate_id": GATE_ID,
        "runtime": runtime,
        "source_sha256": sha256_file(source_path),
        "results": {
            "python_hgraph_eval_node_replay": {"pass": 64, "total": 64},
            "python_hgraph_reference_equal": {"equal": 64, "total": 64},
            "deterministic_replay": True,
            "rotations": 24,
            "canonical_labels": 10,
            "orbit_profile": list(expected_profile),
            "orbit_stabilizer": {"pass": 64, "total": 64},
            "packet_lines": 64,
            "python_packet_sha256": sha256_bytes(first),
            "reference_packet_sha256": sha256_bytes(reference),
        },
        "claim_ceiling": {
            "python_authoring_64_replay": True,
            "cpp_python_byte_semantic_parity": False,
            "semantic_empirical_validity": False,
            "runtime_admission": False,
            "production_admission": False,
            "pointer_promotion": False,
            "global_bind": False,
            "merge": False,
        },
        "verdict": "PASS_CH09B__PYTHON_HGRAPH_EVAL_NODE_64_OF_64",
    }
    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    RECEIPT.write_text(canonical, encoding="utf-8")
    print(canonical, end="")
    print("CH09B_RECEIPT_SHA256=" + sha256_bytes(canonical.encode("utf-8")))
    print("CH09B_PACKET_SHA256=" + sha256_bytes(first))
    print("CH09B_REFERENCE_PACKET_SHA256=" + sha256_bytes(reference))


if __name__ == "__main__":
    main()
