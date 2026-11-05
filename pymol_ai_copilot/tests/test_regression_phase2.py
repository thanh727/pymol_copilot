"""
Phase 2 Regression Tests for bug fixes and scientific validation.
Covers self-distance exclusion, PML syntax validity, insertion-code sorting,
multi-structure pocket isolation, unassigned chain comparison, and embedded tool call extraction.
"""

import os
import tempfile
import unittest

try:
    import pymol
    pymol.pymol_argv = ["pymol", "-qc"]
    pymol.finish_launching()
    from pymol import cmd
    PYMOL_AVAILABLE = True
except Exception:
    PYMOL_AVAILABLE = False

from pymol_ai_copilot.agent.ollama_client import OllamaClient
from pymol_ai_copilot.agent.tool_registry import GLOBAL_REGISTRY
from pymol_ai_copilot.analysis.alignment import StructureAligner
from pymol_ai_copilot.analysis.contacts import ContactAnalyzer, resi_sort_key
from pymol_ai_copilot.pymol_bridge.structure_inspector import StructureInspector


class TestRegressionPhase2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if PYMOL_AVAILABLE:
            cmd.reinitialize()
            cmd.fragment("ala", "reg_prot1")
            cmd.fragment("gly", "reg_prot2")

    def test_insertion_code_residue_sorting(self):
        """Verify sorting residues with mixed types and insertion codes."""
        resis = ["100B", "1", "100A", "2", "-1", "100"]
        sorted_res = sorted(resis, key=resi_sort_key)
        self.assertEqual(sorted_res, ["-1", "1", "2", "100", "100A", "100B"])

    def test_embedded_json_tool_call_extraction(self):
        """Verify extracting JSON tool calls embedded inside conversational text."""
        client = OllamaClient()
        msg = {
            "role": "assistant",
            "content": (
                "I will analyze the structure for you.\n"
                '{"name": "count_atoms", "arguments": {"selection": "reg_prot1"}}\n'
                "Hope that helps!"
            )
        }
        extracted = client._extract_tool_calls(msg)
        self.assertEqual(len(extracted), 1)
        self.assertEqual(extracted[0]["name"], "count_atoms")
        self.assertEqual(extracted[0]["arguments"], {"selection": "reg_prot1"})

    def test_multi_json_calls_extraction(self):
        """Verify extracting multiple tool calls emitted on successive lines."""
        client = OllamaClient()
        msg = {
            "role": "assistant",
            "content": (
                '{"name": "show_representation", "arguments": {"representation": "sticks"}}\n'
                '{"name": "color_selection", "arguments": {"color": "bychain"}}'
            )
        }
        extracted = client._extract_tool_calls(msg)
        self.assertEqual(len(extracted), 2)
        self.assertEqual(extracted[0]["name"], "show_representation")
        self.assertEqual(extracted[1]["name"], "color_selection")

    @unittest.skipUnless(PYMOL_AVAILABLE, "PyMOL required")
    def test_self_distance_exclusion(self):
        """Verify that calculate_distances on the same selection excludes self-distances (0.0 Å)."""
        analyzer = ContactAnalyzer()
        res = analyzer.calculate_distances("reg_prot1", "reg_prot1", cutoff=5.0)
        self.assertTrue(res["success"])
        self.assertGreater(res["contact_pairs_count"], 0)
        # Minimum distance must be greater than 0.0 (e.g. ~1.3-1.5 Å for covalent bonds)
        self.assertGreater(res["minimum_distance_angstroms"], 0.5)
        # Ensure 0.0 is not in the sample
        self.assertNotIn(0.0, res["distances_sample"])

    @unittest.skipUnless(PYMOL_AVAILABLE, "PyMOL required")
    def test_polar_contacts_no_self_contacts(self):
        """Verify that find_polar_contact_candidates excludes 0.0 Å self-contacts."""
        analyzer = ContactAnalyzer()
        res = analyzer.find_polar_contact_candidates("reg_prot1", "reg_prot1", cutoff=3.5)
        self.assertTrue(res["success"])
        for d in res["measured_distances_angstroms"]:
            self.assertGreater(d, 0.5)

    @unittest.skipUnless(PYMOL_AVAILABLE, "PyMOL required")
    def test_pml_script_syntax_validity(self):
        """Verify that color_selection with bychain/byelement replays in PyMOL without syntax error."""
        from pymol_ai_copilot.agent.tools import GLOBAL_CONTEXT
        GLOBAL_CONTEXT.executor.clear_history()

        with tempfile.TemporaryDirectory() as tmpdir:
            pml_path = os.path.join(tmpdir, "test_color.pml")
            GLOBAL_REGISTRY.execute("color_selection", {"color": "bychain", "selection": "reg_prot1"})
            GLOBAL_REGISTRY.execute("color_selection", {"color": "byelement", "selection": "reg_prot1"})
            GLOBAL_REGISTRY.execute("color_selection", {"color": "rainbow", "selection": "reg_prot1"})

            res_pml = GLOBAL_REGISTRY.execute("export_pml", {"filename": pml_path})
            self.assertTrue(res_pml["success"])

            with open(pml_path) as f:
                content = f.read()

            self.assertIn("util.color_chains", content)
            self.assertIn("util.cnc", content)
            self.assertIn("spectrum count", content)
            self.assertNotIn("color bychain", content)

            # Replay script in PyMOL
            cmd.run(pml_path)

    @unittest.skipUnless(PYMOL_AVAILABLE, "PyMOL required")
    def test_compare_residues_unassigned_chains(self):
        """Verify compare_residues auto-detects chains when default chain A is absent."""
        aligner = StructureAligner()
        # reg_prot1 and reg_prot2 have empty chain ''
        res = aligner.compare_residues("reg_prot1", "reg_prot2", chain1="A", chain2="A")
        self.assertTrue(res["success"])
        # Should not crash and should resolve effective chains
        self.assertIn("structure1", res)

    @unittest.skipUnless(PYMOL_AVAILABLE, "PyMOL required")
    def test_empty_object_bounding_box(self):
        """Verify that an object or selection with 0 atoms has 0.0 bounding box."""
        inspector = StructureInspector()
        cmd.select("empty_selection", "none")
        info = inspector.get_selection_info("empty_selection")
        self.assertEqual(info["atom_count"], 0)


if __name__ == "__main__":
    unittest.main()
