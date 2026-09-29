import unittest

from ess15_adversarial_validation import (
    AdversarialFaultInjector,
    EnvelopePolicy,
    FaultType,
    RouteIsolationHarness,
    TaskExecutionEnvelope,
    ValidationVerdict,
    run_validation_suite,
)


class ESS15AdversarialValidationTests(unittest.TestCase):
    def setUp(self):
        self.envelope = TaskExecutionEnvelope(
            EnvelopePolicy(
                expected_authority_token=AdversarialFaultInjector.VALID_TOKEN,
                max_payload_bytes=4096,
            )
        )

    def _evaluate_fault(self, fault):
        raw_response, token = AdversarialFaultInjector.simulate_plugin_response(fault)
        return self.envelope.evaluate_payload(raw_response, token)

    def test_01_clean_path_passes(self):
        self.assertEqual(
            self._evaluate_fault(FaultType.NONE),
            ValidationVerdict.PASS,
        )

    def test_02_network_timeout_holds(self):
        self.assertEqual(
            self._evaluate_fault(FaultType.NETWORK_TIMEOUT),
            ValidationVerdict.HOLD,
        )

    def test_03_malformed_json_holds(self):
        self.assertEqual(
            self._evaluate_fault(FaultType.MALFORMED_JSON),
            ValidationVerdict.HOLD,
        )

    def test_04_rate_limit_holds(self):
        self.assertEqual(
            self._evaluate_fault(FaultType.RATE_LIMIT_EXCEEDED),
            ValidationVerdict.HOLD,
        )

    def test_05_authority_mismatch_holds(self):
        self.assertEqual(
            self._evaluate_fault(FaultType.AUTHORITY_MISMATCH),
            ValidationVerdict.HOLD,
        )

    def test_06_contradictory_pass_invalid_authority_holds(self):
        self.assertEqual(
            self._evaluate_fault(FaultType.CONTRADICTORY_PASS_INVALID_AUTHORITY),
            ValidationVerdict.HOLD,
        )

    def test_payload_bound_rejects_oversized_response(self):
        raw = '{"status":200,"data":"' + ("x" * 5000) + '","source":"Wolfram"}'
        self.assertEqual(
            self.envelope.evaluate_payload(
                raw,
                AdversarialFaultInjector.VALID_TOKEN,
            ),
            ValidationVerdict.HOLD,
        )

    def test_schema_rejects_unknown_field(self):
        raw = (
            '{"status":200,"data":"ok","source":"Wolfram",'
            '"unexpected":"not-allowed"}'
        )
        self.assertEqual(
            self.envelope.evaluate_payload(
                raw,
                AdversarialFaultInjector.VALID_TOKEN,
            ),
            ValidationVerdict.HOLD,
        )

    def test_route_isolation(self):
        harness = RouteIsolationHarness(self.envelope)

        raw_a, token_a = AdversarialFaultInjector.simulate_plugin_response(
            FaultType.MALFORMED_JSON
        )
        self.assertEqual(
            harness.evaluate("route-a", raw_a, token_a),
            ValidationVerdict.HOLD,
        )
        self.assertIsNone(harness.route_state("route-b"))

        raw_b, token_b = AdversarialFaultInjector.simulate_plugin_response(
            FaultType.NONE
        )
        self.assertEqual(
            harness.evaluate("route-b", raw_b, token_b),
            ValidationVerdict.PASS,
        )
        self.assertEqual(
            harness.route_state("route-a"),
            ValidationVerdict.HOLD,
        )
        self.assertEqual(
            harness.route_state("route-b"),
            ValidationVerdict.PASS,
        )

    def test_suite_summary_is_deterministic(self):
        first = run_validation_suite()
        second = run_validation_suite()
        self.assertEqual(first, second)
        self.assertEqual(len(first), 6)


if __name__ == "__main__":
    unittest.main()
