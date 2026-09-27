import unittest
from reconstructed_model import EXPECTED, metrics

class ReconstructedModelTest(unittest.TestCase):
    def test_reconstructed_observables_match_frozen_targets(self):
        self.assertEqual(metrics(), EXPECTED)

if __name__ == "__main__":
    unittest.main()
