import unittest
from fractions import Fraction
from math import comb

import eq64_hgraph_cech_static_operator_kernel as k


class StaticKernelContractTests(unittest.TestCase):
    def test_frozen_kernel_metadata(self):
        m = k.kernel_metadata()
        self.assertEqual(m["kernel_id"], "EQ64__HGRAPH_CECH_STATIC_OPERATOR_KERNEL_V1")
        self.assertEqual(
            m["predecessor_id"],
            "EQ64__Q6_Q3_CECH_ALL_HIGHER_EXACTNESS_AND_CONTRACTING_HOMOTOPY_V1",
        )
        self.assertEqual(m["coefficient_system"], "FUNCTION_SHEAF_R")
        self.assertEqual(m["local_vertex_count"], 20)
        self.assertEqual(m["global_component_count"], 64)
        self.assertEqual(m["vertex_order"], list(range(1, 21)))
        self.assertEqual(m["apex_vertex"], 1)
        self.assertTrue(m["graph_composition_first"])
        self.assertFalse(m["state_lifecycle_logic"])
        self.assertFalse(m["dynamic_topology"])
        self.assertFalse(m["runtime_admission"])
        self.assertFalse(m["global_bind"])
        self.assertTrue(m["zero_spend"])

    def test_dimensions_all_degrees(self):
        for p in range(20):
            self.assertEqual(k.local_dimension(p), comb(20, p + 1))
            self.assertEqual(k.global_dimension(p), 64 * comb(20, p + 1))

    def test_expected_ranks_and_cohomology_all_degrees(self):
        for p in range(20):
            expected_rank = 0 if p == 19 else comb(19, p + 1)
            self.assertEqual(k.expected_delta_rank(p), expected_rank)
            self.assertEqual(
                k.expected_local_cohomology_dimension(p),
                1 if p == 0 else 0,
            )
            self.assertEqual(
                k.expected_global_cohomology_dimension(p),
                64 if p == 0 else 0,
            )

    def test_orientation_rejects_unsorted_or_duplicate_simplex(self):
        with self.assertRaises(ValueError):
            k.validate_simplex((2, 1))
        with self.assertRaises(ValueError):
            k.validate_simplex((1, 1))

    def test_delta0_exact_example(self):
        phi = {(1,): Fraction(2), (2,): Fraction(5)}
        out = k.delta_local(0, phi)
        self.assertEqual(out[(1, 2)], Fraction(3))
        self.assertNotIn((2, 1), out)

    def test_projection0_is_apex_constant(self):
        phi = {(1,): Fraction(7, 3), (5,): Fraction(-2)}
        out = k.projection0_local(phi)
        self.assertEqual(len(out), 20)
        self.assertEqual(set(out.values()), {Fraction(7, 3)})

    def test_operator_graph_rejects_degree_mismatch(self):
        with self.assertRaises(ValueError):
            k.compose(k.delta_operator(1), k.delta_operator(1))
        with self.assertRaises(ValueError):
            k.add_operators(k.delta_operator(0), k.identity_operator(0))

    def test_delta_squared_zero_all_degrees_on_deterministic_probes(self):
        for p in range(18):
            for seed in range(4):
                probe = k.deterministic_probe(p, seed)
                self.assertEqual(
                    k.delta_local(p + 1, k.delta_local(p, probe)),
                    {},
                )

    def test_positive_degree_contracting_homotopy_all_degrees(self):
        for p in range(1, 20):
            op = k.contraction_operator(p)
            for seed in range(4):
                probe = k.deterministic_probe(p, seed)
                self.assertEqual(op(probe), k.identity_local(p, probe))

    def test_degree0_homotopy_is_identity_minus_projection(self):
        lhs = k.degree0_homotopy_operator()
        rhs = k.degree0_reduced_identity_operator()
        for seed in range(8):
            probe = k.deterministic_probe(0, seed)
            self.assertEqual(lhs(probe), rhs(probe))

    def test_basis_level_signs_for_delta1(self):
        e12 = {(1, 2): Fraction(1)}
        self.assertEqual(
            k.delta_local(1, e12)[(1, 2, 3)],
            Fraction(1),
        )
        e13 = {(1, 3): Fraction(1)}
        self.assertEqual(
            k.delta_local(1, e13)[(1, 2, 3)],
            Fraction(-1),
        )
        e23 = {(2, 3): Fraction(1)}
        self.assertEqual(
            k.delta_local(1, e23)[(1, 2, 3)],
            Fraction(1),
        )

    def test_homotopy_apex_rule(self):
        phi = {
            (1, 2, 3): Fraction(11),
            (2, 3, 4): Fraction(99),
        }
        out = k.homotopy_local(2, phi)
        self.assertEqual(out.get((2, 3)), Fraction(11))
        self.assertNotIn((1, 2), out)
        self.assertNotIn((2, 4), out)

    def test_top_degree_delta_zero_and_contraction_identity(self):
        top = {tuple(range(1, 21)): Fraction(13, 5)}
        self.assertEqual(k.delta_local(19, top), {})
        self.assertEqual(k.contraction_operator(19)(top), top)

    def test_componentwise_global_direct_sum_all_64_components(self):
        probe = {}
        for component in range(64):
            probe[(component, (1,))] = Fraction(component + 1)
            probe[(component, (2,))] = Fraction(2 * component - 3)
        out = k.apply_global_componentwise(
            0,
            probe,
            k.delta_operator(0),
        )
        for component in range(64):
            expected_local = k.delta_local(
                0,
                {
                    (1,): Fraction(component + 1),
                    (2,): Fraction(2 * component - 3),
                },
            )
            observed_local = {
                simplex: value
                for (seen_component, simplex), value in out.items()
                if seen_component == component
            }
            self.assertEqual(observed_local, expected_local)

    def test_componentwise_positive_homotopy_identity_selected_degrees_all_components(self):
        for p in (1, 2, 9, 18, 19):
            probe = {}
            local = k.deterministic_probe(p, seed=p)
            for component in range(64):
                scale = component + 1
                for simplex, value in local.items():
                    probe[(component, simplex)] = value * scale
            op = k.contraction_operator(p)
            self.assertEqual(
                k.apply_global_componentwise(p, probe, op),
                probe,
            )

    def test_linearity_delta_h_and_projection(self):
        a0 = {(1,): Fraction(2), (3,): Fraction(7)}
        b0 = {(2,): Fraction(5), (3,): Fraction(-1)}
        self.assertEqual(
            k.delta_local(0, k.add_local(a0, b0)),
            k.add_local(k.delta_local(0, a0), k.delta_local(0, b0)),
        )
        self.assertEqual(
            k.projection0_local(k.add_local(a0, b0)),
            k.add_local(k.projection0_local(a0), k.projection0_local(b0)),
        )

        a2 = {
            (1, 2, 3): Fraction(3),
            (2, 4, 5): Fraction(8),
        }
        b2 = {
            (1, 2, 3): Fraction(-1),
            (1, 4, 5): Fraction(6),
        }
        self.assertEqual(
            k.homotopy_local(2, k.add_local(a2, b2)),
            k.add_local(k.homotopy_local(2, a2), k.homotopy_local(2, b2)),
        )


if __name__ == "__main__":
    unittest.main()
