import unittest
from admissibility_spec_v1 import Evidence, FitState, ControlState, assess_fit, assess_control
class GateTests(unittest.TestCase):
    def test_m4_nonconvergence(self):
        self.assertEqual(assess_fit(Evidence(False,-617.527675,exact_provenance=True)),FitState.INADMISSIBLE)
    def test_m5_indefinite_despite_convergence(self):
        self.assertEqual(assess_fit(Evidence(True,-.3834706,finite_fit_measures=True,critical_warning=True,exact_provenance=True)),FitState.INADMISSIBLE)
    def test_missing_provenance(self):
        self.assertEqual(assess_fit(Evidence(True,.1,finite_fit_measures=True,critical_warning=False)),FitState.MISSING)
    def test_missing_diagnostics(self):
        self.assertEqual(assess_fit(Evidence(True,.1,exact_provenance=True)),FitState.MISSING)
    def test_good_diagnostic_only(self):
        self.assertEqual(assess_fit(Evidence(True,.1,finite_fit_measures=True,critical_warning=False,exact_provenance=True)),FitState.ADMISSIBLE)
    def test_zero_eigen(self):
        self.assertEqual(assess_fit(Evidence(True,0,finite_fit_measures=True,critical_warning=False,exact_provenance=True)),FitState.INADMISSIBLE)
    def test_nan_eigen(self):
        self.assertEqual(assess_fit(Evidence(True,float("nan"),finite_fit_measures=True,critical_warning=False,exact_provenance=True)),FitState.MISSING)
    def test_m4_boundary_holds(self):
        self.assertEqual(assess_control(FitState.INADMISSIBLE,FitState.ADMISSIBLE,False),ControlState.UNKNOWN)
    def test_m5_bounded_reject_candidate(self):
        self.assertEqual(assess_control(FitState.INADMISSIBLE,FitState.ADMISSIBLE,True),ControlState.REJECT)
    def test_missing_alternative(self):
        self.assertEqual(assess_control(FitState.INADMISSIBLE,FitState.MISSING,True),ControlState.UNKNOWN)
    def test_both_admissible_not_selection(self):
        self.assertEqual(assess_control(FitState.ADMISSIBLE,FitState.ADMISSIBLE,True),ControlState.NOT_REJECTED)
if __name__=="__main__": unittest.main()
