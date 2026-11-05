"""
Tests for CapabilityRegistry, WorkflowRegistry, EntityExtractor, and context-dependent tool scoping.
"""

import unittest
from pymol_ai_copilot.agent.capability_registry import GLOBAL_CAPABILITY_REGISTRY, Capability
from pymol_ai_copilot.agent.workflow_engine import GLOBAL_WORKFLOW_REGISTRY, EntityExtractor


class TestCapabilityAndWorkflowEngine(unittest.TestCase):

    # --- CapabilityRegistry tests ---

    def test_capability_registry_total_and_authorized_count(self):
        """Verify that capability registry contains both discovered and authorized tools."""
        all_caps = GLOBAL_CAPABILITY_REGISTRY.list_capabilities(authorized_only=False)
        auth_caps = GLOBAL_CAPABILITY_REGISTRY.list_authorized_tools()

        self.assertGreaterEqual(len(all_caps), 488)
        self.assertEqual(len(auth_caps), 47)

    def test_unreviewed_apis_are_strictly_unauthorized(self):
        """Verify that unreviewed discovered APIs cannot be executed autonomously."""
        # Check an unreviewed API like 'reinitialize' or 'system'
        reinit_cap = GLOBAL_CAPABILITY_REGISTRY.get("reinitialize") or GLOBAL_CAPABILITY_REGISTRY.get("cmd.reinitialize")
        if reinit_cap:
            self.assertFalse(reinit_cap.is_authorized())
            self.assertIn(reinit_cap.status, ["unreviewed_unauthorized", "blocked"])

        res = GLOBAL_CAPABILITY_REGISTRY.execute("system", {"cmd": "ls"})
        self.assertFalse(res["success"])
        self.assertTrue(res.get("unauthorized", False))
        self.assertTrue(res.get("non_retryable", False))

    def test_authorized_tools_have_required_metadata(self):
        """Verify that all 35 authorized tools have IDs, API mappings, schemas, and risk tiers."""
        for cap in GLOBAL_CAPABILITY_REGISTRY.list_authorized_tools():
            self.assertTrue(cap.is_authorized())
            self.assertTrue(len(cap.id) > 0)
            self.assertTrue(len(cap.api_mapping) > 0)
            self.assertIn("type", cap.parameters)
            self.assertTrue(cap.risk_level.startswith("Tier"))
            self.assertIsNotNone(cap.func)

    def test_scoped_ollama_tools_filtering(self):
        """Verify context-dependent tool selection: scoping tools to a specific subset."""
        subset = ["fetch_structure", "show_representation", "color_selection"]
        scoped = GLOBAL_CAPABILITY_REGISTRY.get_ollama_tools(subset=subset)

        self.assertEqual(len(scoped), 3)
        names = [t["function"]["name"] for t in scoped]
        self.assertCountEqual(names, subset)

    # --- EntityExtractor tests ---

    def test_extract_pdb_id(self):
        """Verify extraction of 4-character PDB code and AlphaFold ID."""
        ent1 = EntityExtractor.extract_entities("Download PDB 1UBQ and color it.")
        self.assertEqual(ent1.get("pdb_id"), "1ubq")

        ent2 = EntityExtractor.extract_entities("Tải cấu trúc 4ake dạng cartoon.")
        self.assertEqual(ent2.get("pdb_id"), "4ake")

        ent3 = EntityExtractor.extract_entities("Inspect AF-P04637-F1 model.")
        self.assertEqual(ent3.get("pdb_id"), "af-p04637-f1")

    def test_extract_mutation_notation(self):
        """Verify extraction of standard mutation notations like R132H, Arg132His, A:R132H."""
        ent1 = EntityExtractor.extract_entities("Analyze mutation R132H in chain A.")
        self.assertEqual(ent1.get("mutation"), "R132H")
        self.assertEqual(ent1.get("mutation_pos"), 132)
        self.assertEqual(ent1.get("mutation_wt"), "R")
        self.assertEqual(ent1.get("mutation_mut"), "H")

        ent2 = EntityExtractor.extract_entities("Kiểm tra đột biến K28A tại chuỗi B.")
        self.assertEqual(ent2.get("mutation"), "K28A")
        self.assertEqual(ent2.get("mutation_pos"), 28)

    def test_extract_distance_cutoff(self):
        """Verify extraction of distance thresholds in angstroms."""
        ent1 = EntityExtractor.extract_entities("Find residues within 5.0 angstroms of the ligand.")
        self.assertEqual(ent1.get("cutoff"), 5.0)

        ent2 = EntityExtractor.extract_entities("Tìm các tương tác trong phạm vi 3.5 Å.")
        self.assertEqual(ent2.get("cutoff"), 3.5)

    # --- WorkflowRegistry matching tests ---

    def test_match_wf01_structure_acquisition(self):
        """Verify matching WF01 for English and Vietnamese acquisition prompts."""
        wf_en, ent_en, conf_en = GLOBAL_WORKFLOW_REGISTRY.match_workflow("Download PDB 1UBQ and show cartoon.")
        self.assertIsNotNone(wf_en)
        self.assertEqual(wf_en.workflow_id, "WF01")
        self.assertEqual(ent_en.get("pdb_id"), "1ubq")
        self.assertGreaterEqual(conf_en, 0.5)

        wf_vn, ent_vn, conf_vn = GLOBAL_WORKFLOW_REGISTRY.match_workflow("Tải về cấu trúc 1ubq và hiển thị.")
        self.assertIsNotNone(wf_vn)
        self.assertEqual(wf_vn.workflow_id, "WF01")
        self.assertEqual(ent_vn.get("pdb_id"), "1ubq")

    def test_match_wf02_structural_inspection(self):
        """Verify matching WF02 for structure description."""
        wf, ent, conf = GLOBAL_WORKFLOW_REGISTRY.match_workflow("Describe the loaded protein and its structural features.")
        self.assertIsNotNone(wf)
        self.assertEqual(wf.workflow_id, "WF02")

        wf_vn, _, _ = GLOBAL_WORKFLOW_REGISTRY.match_workflow("Mô tả cấu trúc protein hiện tại.")
        self.assertIsNotNone(wf_vn)
        self.assertEqual(wf_vn.workflow_id, "WF02")

    def test_match_wf03_structure_comparison(self):
        """Verify matching WF03 for alignment and RMSD calculation."""
        wf, ent, conf = GLOBAL_WORKFLOW_REGISTRY.match_workflow(
            "Compare these two proteins and calculate RMSD.",
            session_objects=["1ake", "4ake"]
        )
        self.assertIsNotNone(wf)
        self.assertEqual(wf.workflow_id, "WF03")
        self.assertIn("align_structures", wf.required_capabilities)

    def test_match_wf04_mutation_neighborhood(self):
        """Verify matching WF04 for mutation analysis."""
        wf, ent, conf = GLOBAL_WORKFLOW_REGISTRY.match_workflow("Analyze mutation R132H and identify nearby residues.")
        self.assertIsNotNone(wf)
        self.assertEqual(wf.workflow_id, "WF04")
        self.assertEqual(ent.get("mutation"), "R132H")
        self.assertIn("analyze_mutation", wf.required_capabilities)

    def test_match_wf05_publication_visualization(self):
        """Verify matching WF05 for publication figure preparation."""
        wf, ent, conf = GLOBAL_WORKFLOW_REGISTRY.match_workflow("Prepare a publication-ready protein figure with white background.")
        self.assertIsNotNone(wf)
        self.assertEqual(wf.workflow_id, "WF05")
        self.assertIn("export_png", wf.required_capabilities)
        self.assertIn("set_background", wf.required_capabilities)


if __name__ == "__main__":
    unittest.main()

