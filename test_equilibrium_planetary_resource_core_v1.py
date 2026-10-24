import unittest
import equilibrium_planetary_resource_core_v1 as m


class PlanetaryResourceCore40(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = {r.id: r for r in m.run_validation_matrix()}


def _make_test(i):
    def test(self):
        r = self.results[f"V{i:02d}"]
        self.assertTrue(r.passed, f"{r.id} failed: {r.observed}")
    test.__name__ = f"test_V{i:02d}"
    return test


for _i in range(1, 41):
    setattr(PlanetaryResourceCore40, f"test_V{_i:02d}", _make_test(_i))


if __name__ == "__main__":
    unittest.main(verbosity=2)
