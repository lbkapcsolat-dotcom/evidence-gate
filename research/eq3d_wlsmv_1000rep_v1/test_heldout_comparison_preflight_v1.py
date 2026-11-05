import unittest
from heldout_comparison_preflight_v1 import (
    PairEvidence, Comparison, comparison_preflight,
    heldout_preflight, wilson_interval, TRUTHS, ATTEMPTS_PER_TRUTH
)
VALID = dict(
    exact_same_data=True,same_ordered_variables=True,same_estimator=True,
    same_parameterization=True,same_thresholds=True,
    regular_nesting_proven=True,both_numerically_admissible=True,
    pinned_version_verified=True,robust_method_supported=True,
    boundary_or_nonregular=False)
READY = dict(protocol_committed=True,seed_schedule_hash="a"*64,
             independent_review=True,bounded_authorization=True,
             original_grid_untouched=True,original_grid_used_as_heldout=False,
             locked_analysis_plan=True)
class ProtocolTests(unittest.TestCase):
    def test_fixed_four_truths_and_budget(self):
        self.assertEqual(TRUTHS,("M3","M4","M5","M7"))
        self.assertEqual(ATTEMPTS_PER_TRUTH*len(TRUTHS),1000)
    def test_nested_comparison_is_only_a_review_candidate(self):
        self.assertEqual(comparison_preflight(PairEvidence(**VALID)),Comparison.ELIGIBLE_FOR_REVIEW)
    def test_non_nested_rejected(self):
        self.assertEqual(comparison_preflight(PairEvidence(**{**VALID,"regular_nesting_proven":False})),Comparison.HOLD)
    def test_unknown_nested_relation_rejected(self):
        self.assertEqual(comparison_preflight(PairEvidence(**{**VALID,"regular_nesting_proven":None})),Comparison.HOLD)
    def test_boundary_rejected(self):
        self.assertEqual(comparison_preflight(PairEvidence(**{**VALID,"boundary_or_nonregular":True})),Comparison.HOLD)
    def test_different_dataset_rejected(self):
        self.assertEqual(comparison_preflight(PairEvidence(**{**VALID,"exact_same_data":False})),Comparison.HOLD)
    def test_different_thresholds_rejected(self):
        self.assertEqual(comparison_preflight(PairEvidence(**{**VALID,"same_thresholds":False})),Comparison.HOLD)
    def test_bad_fit_rejected(self):
        self.assertEqual(comparison_preflight(PairEvidence(**{**VALID,"both_numerically_admissible":False})),Comparison.HOLD)
    def test_unverified_lavaan_support_rejected(self):
        self.assertEqual(comparison_preflight(PairEvidence(**{**VALID,"robust_method_supported":None})),Comparison.HOLD)
    def test_prereg_ready_only_if_all_evidence_exists(self):
        self.assertTrue(heldout_preflight(**READY))
    def test_old_grid_cannot_be_reused_as_heldout(self):
        self.assertFalse(heldout_preflight(**{**READY,"original_grid_used_as_heldout":True}))
    def test_review_missing_blocks(self):
        self.assertFalse(heldout_preflight(**{**READY,"independent_review":False}))
    def test_budget_missing_blocks(self):
        self.assertFalse(heldout_preflight(**{**READY,"bounded_authorization":False}))
    def test_missing_seed_hash_blocks(self):
        self.assertFalse(heldout_preflight(**{**READY,"seed_schedule_hash":None}))
    def test_missing_locked_plan_blocks(self):
        self.assertFalse(heldout_preflight(**{**READY,"locked_analysis_plan":False}))
    def test_wilson_valid(self):
        lo,hi=wilson_interval(0,250)
        self.assertAlmostEqual(lo,0.0,places=14)
        self.assertGreater(hi,0)
        self.assertLess(hi,0.02)
    def test_wilson_invalid_counts_hold(self):
        with self.assertRaises(ValueError): wilson_interval(251,250)
if __name__=="__main__": unittest.main()
