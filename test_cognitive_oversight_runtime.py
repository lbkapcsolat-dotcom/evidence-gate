import copy
import itertools
import json
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from cognitive_oversight_runtime import (
    INTERACTION_MODES,
    build_receipt,
    evaluate_state,
    project_eq64,
    replay_receipt,
)
from cognitive_oversight_runtime_api import Handler


def state(T=1, D=1, P=1, V=1, M="SCAFFOLD", E=2):
    return {
        "task_complexity": T,
        "delegation_depth": D,
        "retained_practice": P,
        "verification_capacity": V,
        "interaction_mode": M,
        "evidence_confidence": E,
    }


class CognitiveOversightRuntimeTests(unittest.TestCase):
    def test_same_task_canary(self):
        self.assertEqual(evaluate_state(state(2,2,0,0,"SUBSTITUTE",2))["decision"], "HOLD")
        self.assertEqual(evaluate_state(state(2,1,1,1,"SCAFFOLD",2))["decision"], "SCAFFOLD")
        self.assertEqual(evaluate_state(state(2,0,1,2,"HUMAN_FIRST",2))["decision"], "HUMAN_FIRST")

    def test_counterexamples(self):
        cases = [
            (state(0,2,1,2,"ASSIST",2), "DUAL_CHECK"),
            (state(1,1,1,0,"SCAFFOLD",2), "HUMAN_FIRST"),
            (state(1,0,1,2,"HUMAN_FIRST",0), "HOLD"),
            (state(0,0,1,2,"AUTO",2), "AUTO"),
            (state(2,0,1,2,"AUTO",2), "SCAFFOLD"),
            (state(0,0,0,2,"AUTO",2), "DUAL_CHECK"),
        ]
        for payload, expected in cases:
            self.assertEqual(evaluate_state(payload)["decision"], expected)

    def test_all_972_states_deterministic(self):
        seen = 0
        for values in itertools.product(range(3), range(3), range(2), range(3), INTERACTION_MODES, range(3)):
            T,D,P,V,M,E = values
            payload = state(T,D,P,V,M,E)
            a = build_receipt(payload)
            b = build_receipt(copy.deepcopy(payload))
            self.assertEqual(a, b)
            self.assertTrue(replay_receipt(a)["valid"])
            seen += 1
        self.assertEqual(seen, 972)

    def test_monotonicity(self):
        rank = lambda p: evaluate_state(p)["decision_rank"]
        violations = []
        for T,D,P,M in itertools.product(range(3),range(3),range(2),INTERACTION_MODES):
            for V in range(3):
                for E in range(2):
                    if rank(state(T,D,P,V,M,E+1)) < rank(state(T,D,P,V,M,E)):
                        violations.append(("evidence",T,D,P,V,M,E))
            for E in range(3):
                for V in range(2):
                    if rank(state(T,D,P,V+1,M,E)) < rank(state(T,D,P,V,M,E)):
                        violations.append(("verification",T,D,P,V,M,E))
        for T,D,V,M,E in itertools.product(range(3),range(3),range(3),INTERACTION_MODES,range(3)):
            if rank(state(T,D,1,V,M,E)) < rank(state(T,D,0,V,M,E)):
                violations.append(("practice",T,D,V,M,E))
        for T,P,V,M,E in itertools.product(range(3),range(2),range(3),INTERACTION_MODES,range(3)):
            for D in range(2):
                if rank(state(T,D+1,P,V,M,E)) > rank(state(T,D,P,V,M,E)):
                    violations.append(("delegation",T,D,P,V,M,E))
        for D,P,V,M,E in itertools.product(range(3),range(2),range(3),INTERACTION_MODES,range(3)):
            for T in range(2):
                if rank(state(T+1,D,P,V,M,E)) > rank(state(T,D,P,V,M,E)):
                    violations.append(("complexity",T,D,P,V,M,E))
        self.assertEqual(violations, [])

    def test_eq64_64_of_64_and_downset(self):
        dims = ("task_bounded","delegation_bounded","practice_preserved","independent_verification","human_check_preserving_mode","evidence_adequate")
        order = {"HOLD":0,"HUMAN_FIRST":1,"DUAL_CHECK":2,"SCAFFOLD":3,"ASSIST":4}
        states = {}
        for bits in itertools.product([False,True], repeat=6):
            states[bits] = project_eq64(dict(zip(dims,bits)))["decision"]
        self.assertEqual(len(states),64)
        edges=0
        for bits,decision in states.items():
            for i,bit in enumerate(bits):
                if bit:
                    lower=list(bits); lower[i]=False; lower=tuple(lower)
                    self.assertLessEqual(order[states[lower]], order[decision])
                    edges += 1
        self.assertEqual(edges,192)
        downset=0
        for upper,ud in states.items():
            for lower,ld in states.items():
                if upper != lower and all(int(x) <= int(y) for x,y in zip(lower,upper)):
                    self.assertLessEqual(order[ld], order[ud])
                    downset += 1
        self.assertEqual(downset,665)

    def test_cli_and_api_parity(self):
        payload=state(2,1,1,1,"SCAFFOLD",2)
        direct=build_receipt(payload)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"in.json"; p.write_text(json.dumps(payload),encoding="utf-8")
            r=subprocess.run([sys.executable,"cognitive_oversight_runtime_cli.py","admit",str(p)],capture_output=True,text=True,cwd=Path(__file__).parent)
            self.assertEqual(r.returncode,0)
            self.assertEqual(json.loads(r.stdout),direct)
        server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        th=threading.Thread(target=server.serve_forever,daemon=True); th.start()
        try:
            req=urllib.request.Request(f"http://127.0.0.1:{server.server_port}/v1/cognitive-oversight/admit",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"},method="POST")
            with urllib.request.urlopen(req) as resp:
                api=json.load(resp)
            self.assertEqual(api,direct)
        finally:
            server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
