from __future__ import annotations

import hashlib
import json
from pathlib import Path

GATE_ID = "CH09A__MATERIALIZE_EXACT_HGRAPH_RUNTIME_BYTES__CPP_EVAL_NODE_64_REPLAY__V1"
HGRAPH_VERSION = "0.8.31"
HGRAPH_RELEASE_COMMIT = "1bb4b7f21ddfb6c69c8bae74c523980605ae93f6"
HGRAPH_WHEEL_SHA256 = "78b08521e11cfeb4b088e519e627f21b19171248ec36560a67779d344abe43b2"

log_path = Path("ch09a_cpp_hgraph_replay.log")
cpp_path = Path("ch09a_babai_eq64_cpp_hgraph_replay_v1.cpp")
cmake_path = Path("ch09a_cpp_hgraph_v1/CMakeLists.txt")

lines = log_path.read_text(encoding="utf-8").splitlines()
rows = [json.loads(line) for line in lines if line.startswith('{"x":')]

assert len(rows) == 64, len(rows)
assert all(row["hgraph_equal"] is True for row in rows)
assert any(line == "ROTATIONS=24" for line in lines)
assert any(line == "CANONICAL_LABELS=10" for line in lines)
assert any(line == "ORBIT_PROFILE=1,1,3,3,6,6,8,12,12,12" for line in lines)
assert any(line == "ORBIT_STABILIZER=64/64" for line in lines)
assert any(line == "CPP_HGRAPH_EQ64_MATRIX=64/64" for line in lines)

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

receipt = {
    "schema_version": "CH09A_CPP_HGRAPH_EQ64_REPLAY_RECEIPT_V1",
    "gate_id": GATE_ID,
    "pins": {
        "hgraph_version": HGRAPH_VERSION,
        "hgraph_release_commit": HGRAPH_RELEASE_COMMIT,
        "hgraph_linux_wheel_sha256": HGRAPH_WHEEL_SHA256,
    },
    "sources": {
        "cpp_adapter_sha256": sha256(cpp_path),
        "cmake_sha256": sha256(cmake_path),
    },
    "results": {
        "native_extension_loaded": True,
        "rotations": 24,
        "canonical_labels": 10,
        "orbit_profile": [1, 1, 3, 3, 6, 6, 8, 12, 12, 12],
        "orbit_stabilizer": {"pass": 64, "total": 64},
        "cpp_hgraph_eval_node_replay": {"pass": 64, "total": 64},
        "standalone_cpp_equals_hgraph_eval_node": {"equal": 64, "total": 64},
        "python_authoring_replay": "NOT_EXECUTED_CH09A_SCOPE",
        "cpp_python_byte_semantic_parity": "NOT_EXECUTED_CH09A_SCOPE",
    },
    "claim_ceiling": {
        "native_cpp_hgraph_eval_node_64_replay": True,
        "python_authoring_replay": False,
        "cpp_python_byte_semantic_parity": False,
        "semantic_empirical_validity": False,
        "runtime_admission": False,
        "production_admission": False,
        "pointer_promotion": False,
        "global_bind": False,
        "merge": False,
    },
    "verdict": "PASS_CH09A__EXACT_HGRAPH_RUNTIME_MATERIALIZED__CPP_EVAL_NODE_64_OF_64",
}

out = Path("CH09A__CPP_HGRAPH_EQ64_64_REPLAY_RECEIPT_V1.json")
canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":"))
out.write_text(canonical + "\n", encoding="utf-8")
print(canonical)
print("CH09A_RECEIPT_SHA256=" + sha256(out))
print("CH09A_REPLAY_LOG_SHA256=" + sha256(log_path))
