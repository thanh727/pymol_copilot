"""
Unit tests for scientific structural analysis modules (Mutation, Contacts, Alignment).
"""

import unittest
from unittest.mock import MagicMock
from pymol_ai_copilot.analysis.batch import BatchStructureAnalyzer
from pymol_ai_copilot.analysis.mutation import MutationAnalyzer
from pymol_ai_copilot.analysis.contacts import ContactAnalyzer, resi_sort_key


class TestAnalysis(unittest.TestCase):
    def setUp(self):
        self.mut_analyzer = MutationAnalyzer()
        self.contact_analyzer = ContactAnalyzer()

    def test_mutation_parsing_single_letter(self):
        res = self.mut_analyzer.parse_mutation_string("R132H")
        self.assertEqual(res["resi"], "132")
        self.assertEqual(res["wildtype_1"], "R")
        self.assertEqual(res["wildtype_3"], "ARG")
        self.assertEqual(res["mutant_1"], "H")
        self.assertEqual(res["mutant_3"], "HIS")
        self.assertIsNone(res["chain"])

    def test_mutation_parsing_with_chain(self):
        res = self.mut_analyzer.parse_mutation_string("A:R132H")
        self.assertEqual(res["chain"], "A")
        self.assertEqual(res["resi"], "132")
        self.assertEqual(res["wildtype_1"], "R")
        self.assertEqual(res["mutant_1"], "H")

    def test_mutation_parsing_three_letter(self):
        res = self.mut_analyzer.parse_mutation_string("Arg132His")
        self.assertEqual(res["resi"], "132")
        self.assertEqual(res["wildtype_1"], "R")
        self.assertEqual(res["mutant_1"], "H")

    def test_mutation_parsing_residue_number_only(self):
        res = self.mut_analyzer.parse_mutation_string("residue 132")
        self.assertEqual(res["resi"], "132")

    def test_contact_categories(self):
        self.assertIn("ARG", self.contact_analyzer.CHARGED_POSITIVE)
        self.assertIn("ASP", self.contact_analyzer.CHARGED_NEGATIVE)
        self.assertIn("LEU", self.contact_analyzer.HYDROPHOBIC_RESIDUES)
        self.assertIn("PHE", self.contact_analyzer.AROMATIC_RESIDUES)

    def test_residue_sort_handles_insertion_codes(self):
        """Residue sorting must not compare ints and strings (e.g. 10 vs 10A)."""
        values = ["100B", "10A", "9", "10", "-1"]
        self.assertEqual(
            sorted(values, key=resi_sort_key),
            ["-1", "9", "10", "10A", "100B"]
        )

    def test_batch_continues_after_single_structure_failure(self):
        """One incompatible structure must not abort the whole batch."""

        class FakeCmd:
            def get_names(self, kind):
                return ["ref", "bad", "good"]

            def color(self, *args, **kwargs):
                pass

            def show(self, *args, **kwargs):
                pass

            def orient(self, *args, **kwargs):
                pass

        class FakeExecutor:
            def __init__(self):
                self.cmd = FakeCmd()

            def run_safe(self, func, *args, **kwargs):
                return func(*args, **kwargs)

            def record_command(self, *args, **kwargs):
                pass

        analyzer = BatchStructureAnalyzer(FakeExecutor())
        analyzer.aligner = MagicMock()

        def fake_align(**kwargs):
            if kwargs["mobile"] == "bad":
                raise ValueError("chain 'A' not found in 'bad'")
            return {
                "rmsd_global_ca": 1.0,
                "rmsd_refined_ca": 0.9,
                "rmsd_refined_all_atom": 1.2,
                "aligned_ca_atoms": 100,
                "refined_ca_atoms": 100,
                "matched_residues": 100
            }

        analyzer.aligner.align_structures.side_effect = fake_align

        res = analyzer.batch_compare_structures(
            structure_names=["ref", "bad", "good"],
            reference_name="ref"
        )

        self.assertEqual(len(res["results"]), 1)
        self.assertEqual(res["results"][0]["structure"], "good")
        self.assertEqual(len(res["failed_structures"]), 1)
        self.assertEqual(res["failed_structures"][0]["structure"], "bad")
        self.assertTrue(res["partial_failure"])


if __name__ == "__main__":
    unittest.main()

