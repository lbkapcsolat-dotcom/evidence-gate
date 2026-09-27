from reconstructed_model import EXPECTED, metrics

def test_reconstructed_observables_match_frozen_targets():
    assert metrics() == EXPECTED
