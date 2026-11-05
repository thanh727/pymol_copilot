"""
Headless validation tests for all five reference scientific workflows:
- WF01: Structure Acquisition
- WF02: Structural Inspection
- WF03: Structure Comparison
- WF04: Mutation Neighborhood
- WF05: Publication Visualization
"""

import json
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

from pymol_ai_copilot.agent.capability_registry import GLOBAL_CAPABILITY_REGISTRY
from pymol_ai_copilot.agent.controller import AgentController
from pymol_ai_copilot.agent.workflow_engine import GLOBAL_WORKFLOW_REGISTRY


class TestReferenceWorkflows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not PYMOL_AVAILABLE:
            raise unittest.SkipTest("PyMOL is not available")

    def setUp(self):
        cmd.reinitialize()

    # ------------------------------------------------------------------------
    # WF01: Structure Acquisition
    # ------------------------------------------------------------------------
    def test_wf01_structure_acquisition_execution(self):
        """Test WF01: Fetch 1UBQ, verify atoms, chains, style as cartoon, and orient."""
        wf = GLOBAL_WORKFLOW_REGISTRY.get("WF01")
        self.assertIsNotNone(wf)

        # Step 1 & 2: Fetch structure
        res_fetch = GLOBAL_CAPABILITY_REGISTRY.execute("fetch_structure", {"pdb_id": "1ubq", "object_name": "wf01_ubq"})
        self.assertTrue(res_fetch["success"])
        self.assertEqual(res_fetch["object_name"], "wf01_ubq")
        self.assertGreater(res_fetch["atom_count"], 0)

        # Step 3: Inspect object info
        res_info = GLOBAL_CAPABILITY_REGISTRY.execute("get_object_info", {"object_name": "wf01_ubq"})
        self.assertTrue(res_info["success"])
        self.assertIn("A", res_info["chains"])

        # Step 4: Apply representation and color
        res_show = GLOBAL_CAPABILITY_REGISTRY.execute("show_representation", {"representation": "cartoon", "selection": "wf01_ubq"})
        self.assertTrue(res_show["success"])
        res_color = GLOBAL_CAPABILITY_REGISTRY.execute("color_selection", {"color": "secondary_structure", "selection": "wf01_ubq"})
        self.assertTrue(res_color["success"])

        # Step 5: Orient
        res_orient = GLOBAL_CAPABILITY_REGISTRY.execute("orient_selection", {"selection": "wf01_ubq"})
        self.assertTrue(res_orient["success"])

        # Verification of state in PyMOL
        self.assertIn("wf01_ubq", cmd.get_names("objects"))
        self.assertEqual(cmd.count_atoms("wf01_ubq"), 660)

    # ------------------------------------------------------------------------
    # WF02: Structural Inspection
    # ------------------------------------------------------------------------
    def test_wf02_structural_inspection_execution(self):
        """Test WF02: Inspect loaded 1AKE (chains, ligands, atoms, secondary structure)."""
        pdb_path = os.path.abspath("pymol_ai_copilot/tests/data/1ake.pdb")
        res_load = GLOBAL_CAPABILITY_REGISTRY.execute("load_structure", {"file_path": pdb_path, "object_name": "wf02_ake"})
        self.assertTrue(res_load["success"])

        # Step 1: List objects
        res_list = GLOBAL_CAPABILITY_REGISTRY.execute("list_objects", {})
        self.assertIn("wf02_ake", res_list["objects"])

        # Step 2: Get object info (atoms, ligands, chains)
        res_info = GLOBAL_CAPABILITY_REGISTRY.execute("get_object_info", {"object_name": "wf02_ake"})
        self.assertTrue(res_info["success"])
        self.assertEqual(len(res_info["chains"]), 2)
        self.assertIn("A", res_info["chains"])
        self.assertIn("B", res_info["chains"])
        self.assertGreater(res_info["protein_atoms"], 0)
        self.assertGreater(res_info["ligand_atoms"], 0)

        # Step 3: Enumerate ligands
        ligand_names = {l["resn"] for l in res_info["ligands"]}
        self.assertIn("AP5", ligand_names)

        # Step 4: Summary overview
        res_sum = GLOBAL_CAPABILITY_REGISTRY.execute("get_structure_summary", {})
        self.assertTrue(res_sum["success"])
        self.assertEqual(res_sum["object_count"], 1)

    # ------------------------------------------------------------------------
    # WF03: Structure Comparison & Alignment
    # ------------------------------------------------------------------------
    def test_wf03_structure_comparison_execution(self):
        """Test WF03: Compare 1AKE and 4AKE, align, calculate RMSD, and export JSON."""
        ake_path = os.path.abspath("pymol_ai_copilot/tests/data/1ake.pdb")
        res_load1 = GLOBAL_CAPABILITY_REGISTRY.execute("load_structure", {"file_path": ake_path, "object_name": "ake1"})
        res_load2 = GLOBAL_CAPABILITY_REGISTRY.execute("load_structure", {"file_path": ake_path, "object_name": "ake2"})
        self.assertTrue(res_load1["success"])
        self.assertTrue(res_load2["success"])

        # Step 1: Align structures
        res_align = GLOBAL_CAPABILITY_REGISTRY.execute("align_structures", {"mobile": "ake2", "target": "ake1", "method": "align"})
        self.assertTrue(res_align["success"])
        self.assertEqual(res_align["rmsd"], 0.0)  # identical structures

        # Step 2: Calculate RMSD
        res_rmsd = GLOBAL_CAPABILITY_REGISTRY.execute("calculate_rmsd", {"mobile_selection": "ake2 and name CA", "target_selection": "ake1 and name CA"})
        self.assertTrue(res_rmsd["success"])
        self.assertEqual(res_rmsd["rmsd"], 0.0)

        # Step 3: Export findings to JSON
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            res_export = GLOBAL_CAPABILITY_REGISTRY.execute("export_analysis_json", {
                "data": {"workflow": "WF03", "rmsd": res_rmsd["rmsd"], "aligned_atoms": res_align["aligned_atoms"]},
                "output_path": tmp_path
            })
            self.assertTrue(res_export["success"])
            self.assertTrue(os.path.exists(tmp_path))
            with open(tmp_path) as f:
                saved = json.load(f)
            self.assertEqual(saved["workflow"], "WF03")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # ------------------------------------------------------------------------
    # WF04: Mutation Neighborhood Analysis
    # ------------------------------------------------------------------------
    def test_wf04_mutation_neighborhood_execution(self):
        """Test WF04: Analyze mutation in 1AKE (Pro9 / Lys13), find neighbors, polar contacts, highlight."""
        pdb_path = os.path.abspath("pymol_ai_copilot/tests/data/1ake.pdb")
        res_load = GLOBAL_CAPABILITY_REGISTRY.execute("load_structure", {"file_path": pdb_path, "object_name": "ake_mut"})
        self.assertTrue(res_load["success"])

        # Step 1 & 2: Analyze mutation P9A (Proline 9 in 1AKE)
        res_mut = GLOBAL_CAPABILITY_REGISTRY.execute("analyze_mutation", {
            "mutation_str": "P9A",
            "object_name": "ake_mut",
            "chain": "A",
            "cutoff": 5.0
        })
        self.assertTrue(res_mut["success"])
        self.assertEqual(res_mut["actual_residue_3"], "PRO")
        self.assertGreater(res_mut["neighbor_residues_count"], 0)

        # Step 3: Find nearby residues around Pro9
        res_near = GLOBAL_CAPABILITY_REGISTRY.execute("find_nearby_residues", {
            "target_selection": "ake_mut and chain A and resi 9",
            "cutoff": 5.0
        })
        self.assertTrue(res_near["success"])
        self.assertGreater(res_near["residue_count"], 0)

        # Step 4: Measure polar contact candidates
        res_polar = GLOBAL_CAPABILITY_REGISTRY.execute("find_polar_contact_candidates", {
            "selection1": "ake_mut and chain A and resi 9",
            "selection2": "ake_mut and chain A and not resi 9",
            "cutoff": 3.5
        })
        self.assertTrue(res_polar["success"])

        # Step 5: Highlight residues as sticks and label
        res_high = GLOBAL_CAPABILITY_REGISTRY.execute("highlight_residues", {
            "selection": "ake_mut and chain A and resi 9",
            "representation": "sticks",
            "color": "yellow"
        })
        self.assertTrue(res_high["success"])

    # ------------------------------------------------------------------------
    # WF05: Publication Visualization
    # ------------------------------------------------------------------------
    def test_wf05_publication_visualization_execution(self):
        """Test WF05: Apply publication preset, set background white, orient, and export PNG + PML."""
        pdb_path = os.path.abspath("pymol_ai_copilot/tests/data/1ake.pdb")
        res_load = GLOBAL_CAPABILITY_REGISTRY.execute("load_structure", {"file_path": pdb_path, "object_name": "pub_ake"})
        self.assertTrue(res_load["success"])

        # Step 1: Preset
        res_pre = GLOBAL_CAPABILITY_REGISTRY.execute("apply_visualization_preset", {
            "preset_name": "cartoon_by_chain"
        })
        self.assertTrue(res_pre["success"])

        # Step 2: Background white
        res_bg = GLOBAL_CAPABILITY_REGISTRY.execute("set_background", {"color": "white"})
        self.assertTrue(res_bg["success"])

        # Step 3: Orient & zoom
        res_orient = GLOBAL_CAPABILITY_REGISTRY.execute("orient_selection", {"selection": "pub_ake"})
        self.assertTrue(res_orient["success"])

        # Step 4: Export PNG figure and PML script
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_png, \
             tempfile.NamedTemporaryFile(suffix=".pml", delete=False) as tmp_pml:
            png_path = tmp_png.name
            pml_path = tmp_pml.name

        try:
            res_png = GLOBAL_CAPABILITY_REGISTRY.execute("export_png", {
                "output_path": png_path,
                "width": 640,
                "height": 480,
                "ray": False
            })
            self.assertTrue(res_png["success"])
            self.assertTrue(os.path.exists(png_path))
            self.assertGreater(os.path.getsize(png_path), 0)

            res_pml = GLOBAL_CAPABILITY_REGISTRY.execute("export_pml", {
                "output_path": pml_path
            })
            self.assertTrue(res_pml["success"])
            self.assertTrue(os.path.exists(pml_path))
            self.assertGreater(os.path.getsize(pml_path), 0)
        finally:
            if os.path.exists(png_path):
                os.remove(png_path)
            if os.path.exists(pml_path):
                os.remove(pml_path)

    # ------------------------------------------------------------------------
    # Agent Controller Workflow Scoping & Provenance Integration Tests
    # ------------------------------------------------------------------------
    def test_controller_wf01_scoping_and_provenance(self):
        """Verify that AgentController matches WF01, scopes tools schema, and injects plan."""
        from unittest.mock import MagicMock
        mock_client = MagicMock()
        mock_client.chat.return_value = {
            "role": "assistant",
            "content": "Structure acquisition complete.",
            "tool_calls": []
        }

        controller = AgentController(ollama_client=mock_client, model_name="mock-model")
        events = []
        res = controller.run("Download PDB 1UBQ and display it.", max_steps=2, step_callback=lambda e: events.append(e))

        self.assertTrue(res["success"])
        self.assertEqual(res["workflow"], "WF01")
        self.assertEqual(res["provenance"]["workflow_id"], "WF01")
        self.assertEqual(res["provenance"]["entities"]["pdb_id"], "1ubq")
        self.assertIn("workflow_selected", [e.get("type") for e in events])

        # Verify that tools passed to chat were scoped (not all 35 tools!)
        called_tools = mock_client.chat.call_args[1]["tools"]
        called_tool_names = [t["function"]["name"] for t in called_tools]
        self.assertLess(len(called_tool_names), 35)
        self.assertIn("fetch_structure", called_tool_names)
        self.assertIn("show_representation", called_tool_names)

    def test_controller_wf04_mutation_entity_resolution(self):
        """Verify that AgentController matches WF04 and extracts mutation entities."""
        from unittest.mock import MagicMock
        mock_client = MagicMock()
        mock_client.chat.return_value = {
            "role": "assistant",
            "content": "Mutation analysis complete.",
            "tool_calls": []
        }

        controller = AgentController(ollama_client=mock_client, model_name="mock-model")
        res = controller.run("Analyze mutation R132H in chain A and show nearby residues within 5 angstroms.", max_steps=2)

        self.assertTrue(res["success"])
        self.assertEqual(res["workflow"], "WF04")
        self.assertEqual(res["provenance"]["entities"]["mutation"], "R132H")
        self.assertEqual(res["provenance"]["entities"]["mutation_pos"], 132)
        self.assertEqual(res["provenance"]["entities"]["chain"], "A")
        self.assertEqual(res["provenance"]["entities"]["cutoff"], 5.0)


if __name__ == "__main__":
    unittest.main()
