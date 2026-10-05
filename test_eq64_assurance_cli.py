import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_eq64_executable_assurance_engine import BASE
from eq64_executable_assurance_engine import evaluate_assurance


class EQ64AssuranceCLITests(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run(
            [sys.executable, "eq64_assurance_cli.py", *args],
            cwd=Path(__file__).parent,
            text=True,
            capture_output=True,
        )

    def test_evaluate_pass_returns_zero_and_writes_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            inp = d / "input.json"
            out = d / "receipt.json"
            inp.write_text(json.dumps(BASE), encoding="utf-8")
            p = self._run("evaluate", str(inp), "--receipt-out", str(out))
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertTrue(out.exists())
            self.assertEqual(json.loads(out.read_text())["decision"], "PASS")

    def test_evaluate_hold_returns_three(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            payload = copy.deepcopy(BASE)
            payload["security"]["status"] = "HOLD"
            inp = d / "input.json"
            inp.write_text(json.dumps(payload), encoding="utf-8")
            p = self._run("evaluate", str(inp))
            self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
            self.assertEqual(json.loads(p.stdout)["decision"], "HOLD")

    def test_replay_valid_and_invalid_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            receipt = evaluate_assurance(BASE)
            good = d / "good.json"
            good.write_text(json.dumps(receipt), encoding="utf-8")
            p = self._run("replay", str(good))
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

            bad_receipt = copy.deepcopy(receipt)
            bad_receipt["decision"] = "HOLD"
            bad = d / "bad.json"
            bad.write_text(json.dumps(bad_receipt), encoding="utf-8")
            p = self._run("replay", str(bad))
            self.assertEqual(p.returncode, 1, p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main()
