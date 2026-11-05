"""
Unit tests for scientific structural analysis modules (Mutation, Contacts, Alignment).
"""

import unittest
from pymol_ai_copilot.analysis.mutation import MutationAnalyzer
from pymol_ai_copilot.analysis.contacts import ContactAnalyzer


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


if __name__ == "__main__":
    unittest.main()

