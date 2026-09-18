import copy
import itertools
import unittest

from ess_evidence_runtime import build_receipt, replay_receipt
from test_ess_evidence_runtime import BASE


class EQ64ExhaustiveTests(unittest.TestCase):
    def test_all_64_boolean_evidence_states(self):
        dims = [
            "historical_identity",
            "fresh_readback",
            "semantic_contract",
            "baseline_bound",
            "admissible_execution",
            "negative_evidence",
        ]
        seen = 0
        for bits in itertools.product([False, True], repeat=6):
            payload = copy.deepcopy(BASE)
            payload["claim"] = "EQ64 exhaustive admission canary"
            payload["eq64"].update(dict(zip(dims, bits)))
            first = build_receipt(payload)
            second = build_receipt(copy.deepcopy(payload))

            if bits[-1]:
                expected = "REJECT"
            elif all(bits[i] for i in (1, 2, 3, 4)):
                expected = "PASS"
            else:
                expected = "HOLD"

            self.assertEqual(first["admission"], expected, bits)
            self.assertEqual(first["receipt_sha256"], second["receipt_sha256"], bits)
            self.assertEqual(first["evidence_id"], second["evidence_id"], bits)
            self.assertTrue(replay_receipt(first)["valid"], bits)
            seen += 1

        self.assertEqual(seen, 64)


if __name__ == "__main__":
    unittest.main()
