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

    def test_show_representation_rejects_empty_selection(self):
        res = GLOBAL_REGISTRY.execute("show_representation", {
            "representation": "sticks",
            "selection": "resn DEFINITELY_NOT_PRESENT"
        })
        self.assertFalse(res["success"])
        self.assertIn("matches 0 atoms", res["error"])

    def test_visual_mutation_tools_reject_empty_selection(self):
        """Colors, camera moves, labels, and transparency must not silently no-op."""
        cases = [
            ("color_selection", {"color": "red", "selection": "resn DEFINITELY_NOT_PRESENT"}),
            ("zoom_selection", {"selection": "resn DEFINITELY_NOT_PRESENT"}),
            ("orient_selection", {"selection": "resn DEFINITELY_NOT_PRESENT"}),
            ("set_transparency", {"transparency": 0.5, "selection": "resn DEFINITELY_NOT_PRESENT"}),
            ("label_residues", {"selection": "resn DEFINITELY_NOT_PRESENT"}),
        ]
        for tool_name, arguments in cases:
            with self.subTest(tool=tool_name):
                res = GLOBAL_REGISTRY.execute(tool_name, arguments)
                self.assertFalse(res["success"], msg=tool_name)
                self.assertIn("matches 0 atoms", res["error"], msg=tool_name)

    def test_bare_residue_name_selection_is_normalized(self):
        """A bare residue name such as 'SO4' must resolve to 'resn SO4'."""
        cmd.delete("norm_ion")
        cmd.pseudoatom("norm_ion", resn="SO4", resi="401", chain="A", pos=[0, 0, 0])
        try:
            res = GLOBAL_REGISTRY.execute("show_representation", {
                "representation": "sticks",
                "selection": "SO4"
            })
            self.assertTrue(res["success"], msg=res.get("error"))
            self.assertEqual(res["selection"], "resn 'SO4'")
            self.assertEqual(res["atom_count"], 1)

            count = GLOBAL_REGISTRY.execute("count_atoms", {"selection": "SO4"})
            self.assertTrue(count["success"])
            self.assertEqual(count["atom_count"], 1)

            nearby = GLOBAL_REGISTRY.execute("find_nearby_residues", {
                "target_selection": "SO4",
                "cutoff": 4.0
            })
            self.assertTrue(nearby["success"], msg=nearby.get("error"))
            self.assertEqual(nearby["target_selection"], "resn 'SO4'")
        finally:
            cmd.delete("norm_ion")

    def test_residue_number_selections_are_not_treated_as_residue_names(self):
        """'resi 441' must stay a residue-number selection, not become resn 'RESI'."""
        executor = GLOBAL_CONTEXT.executor
        self.assertEqual(executor.normalize_selection("resi 441"), "resi 441")
        self.assertEqual(executor.normalize_selection("chain A and resi 441"), "chain A and resi 441")
        self.assertEqual(executor.normalize_selection("residue 441"), "resi '441'")
        self.assertEqual(executor.normalize_selection("residue G441"), "resi '441'")
        self.assertEqual(executor.normalize_selection("G441"), "resi '441'")
        self.assertEqual(executor.normalize_selection("SO4 401"), "resn 'SO4' and resi '401'")

        cmd.delete("resi_probe")
        cmd.pseudoatom("resi_probe", resn="GLY", resi="441", chain="A", name="CA", pos=[0, 0, 0])
        try:
            count = GLOBAL_REGISTRY.execute("count_atoms", {"selection": "resi 441"})
            self.assertTrue(count["success"], msg=count.get("error"))
            self.assertEqual(count["atom_count"], 1)
        finally:
            cmd.delete("resi_probe")

    def test_hide_water_shortcut_hides_solvent(self):
        """'hide water' must hide solvent instead of failing on a rep name."""
        cmd.delete("water_probe")
        cmd.pseudoatom("water_probe", resn="HOH", resi="1", chain="A", pos=[8, 8, 8])
        try:
            self.assertGreater(cmd.count_atoms("solvent"), 0)
            res = GLOBAL_REGISTRY.execute("hide_representation", {
                "representation": "water",
                "selection": "all"
            })
            self.assertTrue(res["success"], msg=res.get("error"))
            self.assertEqual(res["hidden"], "everything")
            self.assertEqual(res["selection"], "solvent")
        finally:
            cmd.delete("water_probe")

    def test_measurement_objects_do_not_break_structure_summary(self):
        """PyMOL distance objects must not be treated as molecular structures."""
        cmd.delete("test_measurement")
        cmd.distance(
            "test_measurement",
            "test_prot1",
            "test_prot2",
            cutoff=100.0,
            mode=2
        )
        try:
            summary = GLOBAL_CONTEXT.inspector.get_structure_summary()
            names = [obj["name"] for obj in summary["objects"]]
            self.assertIn("test_prot1", names)
            self.assertNotIn("test_measurement", names)

            loaded = GLOBAL_CONTEXT.inspector.get_loaded_objects()
            self.assertNotIn("test_measurement", loaded)

            res = GLOBAL_REGISTRY.execute(
                "get_object_info", {"object_name": "test_measurement"}
            )
            self.assertFalse(res["success"])
            self.assertIn("not a molecular object", res["error"])
        finally:
            cmd.delete("test_measurement")

    def test_find_nearby_residues_reports_each_target_instance(self):
        cmd.delete("ion_test")
        cmd.pseudoatom("ion_test", resn="SO4", resi="401", chain="A", pos=[0, 0, 0])
        cmd.pseudoatom("ion_test", resn="SO4", resi="402", chain="A", pos=[4, 0, 0])
        try:
            res = GLOBAL_REGISTRY.execute("find_nearby_residues", {
                "target_selection": "resn SO4",
                "cutoff": 8.0,
                "surrounding_scope": "all"
            })
        finally:
            cmd.delete("ion_test")

        self.assertTrue(res["success"])
        self.assertEqual(res["target_count"], 2)
        self.assertEqual(len(res["per_instance"]), 2)
        self.assertEqual(
            {item["target"]["resi"] for item in res["per_instance"]},
            {"401", "402"}
        )
        for item in res["per_instance"]:
            self.assertIn("residues", item)
            self.assertIn("selection", item)

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

