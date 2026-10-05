from __future__ import annotations
import json, importlib.metadata
import _hgraph
from hgraph import TS, compute_node, graph, operator
from ess_earth2studio_eq64_reference_v1 import Evidence, observe

@operator
def observe_eq64_native(payload:TS[str])->TS[str]: ...

@compute_node(overloads=observe_eq64_native)
def observe_eq64_native_impl(payload:TS[str])->TS[str]:
    return json.dumps(observe(Evidence(**json.loads(payload))),sort_keys=True,separators=(",",":"))

@graph
def earth2studio_assurance_graph(payload:TS[str])->TS[str]:
    return observe_eq64_native(payload)

def runtime_metadata():
    return {"hgraph_version":importlib.metadata.version("hgraph"),"native_extension":str(_hgraph.__file__),"native_loaded":bool(_hgraph.__file__)}
