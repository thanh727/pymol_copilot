"""
Integration tests with running PyMOL instance in headless mode (-qc).
Verifies that tools actually interact with PyMOL's internal state.
"""

import os
import tempfile
import unittest

# Initialize headless PyMOL before running tests
try:
    import pymol
    pymol.pymol_argv = ["pymol", "-qc"]
    pymol.finish_launching()
    from pymol import cmd
    PYMOL_AVAILABLE = True
except Exception as e:
    print(f"PyMOL initialization failed: {e}")
    PYMOL_AVAILABLE = False

from pymol_ai_copilot.agent.tool_registry import GLOBAL_REGISTRY
from pymol_ai_copilot.agent.tools import GLOBAL_CONTEXT


@unittest.skipUnless(PYMOL_AVAILABLE, "PyMOL is not available")
class TestPyMOLIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cmd.reinitialize()
        # Build test structures: alanine dipeptide and glycine
        cmd.fragment("ala", "test_prot1")
        cmd.fragment("gly", "test_prot2")

    def test_list_objects(self):
        res = GLOBAL_REGISTRY.execute("list_objects", {})
        self.assertTrue(res["success"])
        self.assertIn("test_prot1", res["objects"])
        self.assertIn("test_prot2", res["objects"])

    def test_count_atoms(self):
        res = GLOBAL_REGISTRY.execute("count_atoms", {"selection": "test_prot1"})
        self.assertTrue(res["success"])
        self.assertEqual(res["atom_count"], 10)

    def test_get_object_info(self):
        res = GLOBAL_REGISTRY.execute("get_object_info", {"object_name": "test_prot1"})
        self.assertTrue(res["success"])
        self.assertEqual(res["total_atoms"], 10)
        self.assertIn("bounding_box_angstroms", res)

    def test_show_and_hide_representation(self):
        res_show = GLOBAL_REGISTRY.execute("show_representation", {"representation": "sticks", "selection": "test_prot1"})
        self.assertTrue(res_show["success"])

        res_hide = GLOBAL_REGISTRY.execute("hide_representation", {"representation": "sticks", "selection": "test_prot1"})
        self.assertTrue(res_hide["success"])

    def test_color_selection(self):
        res = GLOBAL_REGISTRY.execute("color_selection", {"color": "cyan", "selection": "test_prot1"})
        self.assertTrue(res["success"])

    def test_select_residues(self):
        res = GLOBAL_REGISTRY.execute("select_residues", {"selection_name": "my_ala", "selection_expr": "test_prot1 and resn ALA"})
        self.assertTrue(res["success"])
        self.assertEqual(res["atom_count"], 10)

    def test_calculate_distances(self):
        res = GLOBAL_REGISTRY.execute("calculate_distances", {
            "selection1": "test_prot1 and name CA",
            "selection2": "test_prot1 and name N",
            "cutoff": 5.0
        })
        self.assertTrue(res["success"])
        self.assertGreater(res["contact_pairs_count"], 0)
        self.assertIsNotNone(res["minimum_distance_angstroms"])

    def test_find_nearby_residues(self):
        res = GLOBAL_REGISTRY.execute("find_nearby_residues", {
            "target_selection": "test_prot1 and name CA",
            "cutoff": 6.0,
            "surrounding_scope": "all"
        })
        self.assertTrue(res["success"])

    def test_align_and_rmsd(self):
        res_align = GLOBAL_REGISTRY.execute("align_structures", {
            "mobile": "test_prot2",
            "target": "test_prot1",
            "method": "align"
        })
        self.assertTrue(res_align["success"])
        self.assertIn("rmsd", res_align)

    def test_export_png_and_pml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            png_path = os.path.join(tmpdir, "test.png")
            res_png = GLOBAL_REGISTRY.execute("export_png", {
                "filename": png_path,
                "width": 640,
                "height": 480,
                "ray": 0
            })
            self.assertTrue(res_png["success"])
            self.assertTrue(os.path.exists(res_png["filepath"]))

            pml_path = os.path.join(tmpdir, "test.pml")
            res_pml = GLOBAL_REGISTRY.execute("export_pml", {"filename": pml_path})
            self.assertTrue(res_pml["success"])
            self.assertTrue(os.path.exists(res_pml["filepath"]))

    def test_save_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pse_path = os.path.join(tmpdir, "test_session.pse")
            res_pse = GLOBAL_REGISTRY.execute("save_session", {"filename": pse_path})
            self.assertTrue(res_pse["success"])
            self.assertTrue(os.path.exists(res_pse["filepath"]))


if __name__ == "__main__":
    unittest.main()

