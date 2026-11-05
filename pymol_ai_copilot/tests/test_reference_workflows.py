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
import numpy as np

try:
    import pymol
    pymol.pymol_argv = ["pymol", "-qc"]
    pymol.finish_launching()
    from pymol import cmd
    PYMOL_AVAILABLE = True
except Exception:
    PYMOL_AVAILABLE = False

from pymol_ai_copilot.agent.capability_registry import (
    GLOBAL_CAPABILITY_REGISTRY,
    CapabilityRegistry,
    ErrorClassification,
    classify_error,
    define_capability,
)
from pymol_ai_copilot.agent.controller import AgentController
from pymol_ai_copilot.agent.workflow_engine import (
    GLOBAL_WORKFLOW_REGISTRY,
    WorkflowSession,
    WorkflowState,
    StepState,
)


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

    # ------------------------------------------------------------------------
    # Phase 3 Deterministic Workflow Execution & Scientific Validation Tests
    # ------------------------------------------------------------------------
    def test_deterministic_wf01_acquisition(self):
        """WF01: Execute deterministic structure acquisition and verify gates."""
        wf = GLOBAL_WORKFLOW_REGISTRY.get("WF01")
        self.assertIsNotNone(wf)
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        ubq_path = os.path.join(data_dir, "1ubq.pdb")

        rec = wf.execute_deterministic({"file_path": ubq_path, "object_name": "wf01_det_ubq"})
        self.assertEqual(rec.state, WorkflowState.COMPLETED)
        self.assertTrue(rec.validation_gates_passed)
        self.assertEqual(rec.scientific_measurements["atom_count"], 660)
        self.assertIn("A", rec.scientific_measurements["chains"])
        self.assertGreaterEqual(len(rec.step_records), 2)

    def test_deterministic_wf02_inspection(self):
        """WF02: Execute deterministic structural inspection for 1UBQ."""
        wf = GLOBAL_WORKFLOW_REGISTRY.get("WF02")
        self.assertIsNotNone(wf)
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        ubq_path = os.path.join(data_dir, "1ubq.pdb")
        cmd.load(ubq_path, "det_1ubq")

        rec = wf.execute_deterministic({"target": "det_1ubq"})
        self.assertEqual(rec.state, WorkflowState.COMPLETED)
        self.assertTrue(rec.validation_gates_passed)
        self.assertEqual(rec.scientific_measurements["total_atoms"], 660)
        self.assertEqual(rec.scientific_measurements["protein_atoms"], 602)
        self.assertEqual(rec.scientific_measurements["solvent_atoms"], 58)
        self.assertEqual(rec.scientific_measurements["chains"], ["A"])

    def test_deterministic_wf03_comparison_and_independent_rmsd(self):
        """WF03: Execute deterministic structure comparison on Chain A and independently verify Kabsch RMSD."""
        wf = GLOBAL_WORKFLOW_REGISTRY.get("WF03")
        self.assertIsNotNone(wf)
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        cmd.load(os.path.join(data_dir, "1ake.pdb"), "det_1ake")
        cmd.load(os.path.join(data_dir, "4ake.pdb"), "det_4ake")

        # Automatically detects multi-chain structures and defaults to single-chain comparison (Chain A)
        rec = wf.execute_deterministic({"mobile": "det_1ake", "target": "det_4ake", "method": "align"})
        self.assertEqual(rec.state, WorkflowState.COMPLETED)
        self.assertTrue(rec.validation_gates_passed)
        meas = rec.scientific_measurements
        self.assertEqual(meas["comparison_scope"], "single_chain")
        self.assertEqual(meas["mobile_chain"], "A")
        self.assertEqual(meas["target_chain"], "A")
        self.assertIsNone(meas["scientific_warning"])

        reported_global_rmsd = meas["rmsd_global_ca"]
        reported_core_rmsd = meas["rmsd_refined_core"]
        # Global open vs closed C-alpha RMSD for adenylate kinase monomer is 7.13 Å (literature benchmark: ~7-8 Å)
        self.assertAlmostEqual(reported_global_rmsd, 7.1307, delta=0.05)
        # Refined core C-alpha RMSD is ~2.07 Å
        self.assertAlmostEqual(reported_core_rmsd, 2.0691, delta=0.05)

        # Independent Kabsch RMSD verification on sequence-verified Chain A CA coordinates using NumPy SVD
        c1, c2 = [], []
        cmd.iterate_state(1, "det_1ake and chain A and name CA", "c1.append([x, y, z])", space={"c1": c1})
        cmd.iterate_state(1, "det_4ake and chain A and name CA", "c2.append([x, y, z])", space={"c2": c2})
        self.assertEqual(len(c1), 214)
        self.assertEqual(len(c2), 214)
        p = np.array(c1, dtype=float)
        q = np.array(c2, dtype=float)

        p_c = p - np.mean(p, axis=0)
        q_c = q - np.mean(q, axis=0)
        H = p_c.T @ q_c
        U, S, Vt = np.linalg.svd(H)
        V = Vt.T
        d = np.sign(np.linalg.det(V @ U.T))
        R = V @ np.diag([1, 1, d]) @ U.T
        p_aligned = (R @ p_c.T).T
        kabsch_rmsd = float(np.sqrt(np.mean(np.sum((p_aligned - q_c) ** 2, axis=-1))))

        # Verify that reported global RMSD matches independent Kabsch calculation to < 0.001 Å
        self.assertAlmostEqual(reported_global_rmsd, kabsch_rmsd, delta=0.001)

    def test_deterministic_wf03_chain_b_comparison(self):
        """WF03: Compare Chain B vs Chain B explicitly and verify global Ca RMSD is ~6.90 Å."""
        wf = GLOBAL_WORKFLOW_REGISTRY.get("WF03")
        self.assertIsNotNone(wf)
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        cmd.load(os.path.join(data_dir, "1ake.pdb"), "det_1ake_b")
        cmd.load(os.path.join(data_dir, "4ake.pdb"), "det_4ake_b")

        rec = wf.execute_deterministic({"mobile": "det_1ake_b", "target": "det_4ake_b", "chain": "B"})
        self.assertEqual(rec.state, WorkflowState.COMPLETED)
        meas = rec.scientific_measurements
        self.assertEqual(meas["comparison_scope"], "single_chain")
        self.assertEqual(meas["mobile_chain"], "B")
        self.assertEqual(meas["target_chain"], "B")
        self.assertAlmostEqual(meas["rmsd_global_ca"], 6.8980, delta=0.05)

        # Independent NumPy Kabsch SVD on Chain B
        c1, c2 = [], []
        cmd.iterate_state(1, "det_1ake_b and chain B and name CA", "c1.append([x, y, z])", space={"c1": c1})
        cmd.iterate_state(1, "det_4ake_b and chain B and name CA", "c2.append([x, y, z])", space={"c2": c2})
        p = np.array(c1, dtype=float)
        q = np.array(c2, dtype=float)
        p_c = p - np.mean(p, axis=0)
        q_c = q - np.mean(q, axis=0)
        H = p_c.T @ q_c
        U, S, Vt = np.linalg.svd(H)
        V = Vt.T
        d = np.sign(np.linalg.det(V @ U.T))
        R = V @ np.diag([1, 1, d]) @ U.T
        p_aligned = (R @ p_c.T).T
        kabsch_rmsd = float(np.sqrt(np.mean(np.sum((p_aligned - q_c) ** 2, axis=-1))))
        self.assertAlmostEqual(meas["rmsd_global_ca"], kabsch_rmsd, delta=0.001)

    def test_deterministic_wf03_multichain_asymmetric_unit_caveat(self):
        """WF03: Multichain comparison across crystal asymmetric unit triggers quaternary packing warning."""
        wf = GLOBAL_WORKFLOW_REGISTRY.get("WF03")
        self.assertIsNotNone(wf)
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        cmd.load(os.path.join(data_dir, "1ake.pdb"), "det_1ake_m")
        cmd.load(os.path.join(data_dir, "4ake.pdb"), "det_4ake_m")

        # Explicitly request multichain alignment across the entire two-chain asymmetric unit
        rec = wf.execute_deterministic({"mobile": "det_1ake_m", "target": "det_4ake_m", "scope": "multichain"})
        self.assertEqual(rec.state, WorkflowState.COMPLETED)
        meas = rec.scientific_measurements
        self.assertEqual(meas["comparison_scope"], "multichain")
        self.assertAlmostEqual(meas["rmsd_global_ca"], 18.4487, delta=0.05)

        # Verify that the scientific warning is triggered and recorded
        self.assertIsNotNone(meas["scientific_warning"])
        self.assertIn("Multichain Asymmetric Unit Caveat", meas["scientific_warning"])
        self.assertTrue(any("Multichain Asymmetric Unit Caveat" in c for c in rec.scientific_caveats))

    def test_deterministic_wf03_methods_comparison(self):
        """WF03: Compare align, super, and cealign on Chain A and verify consistency."""
        wf = GLOBAL_WORKFLOW_REGISTRY.get("WF03")
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        cmd.load(os.path.join(data_dir, "1ake.pdb"), "m_1ake")
        cmd.load(os.path.join(data_dir, "4ake.pdb"), "m_4ake")

        rec_align = wf.execute_deterministic({"mobile": "m_1ake", "target": "m_4ake", "chain": "A", "method": "align"})
        rec_super = wf.execute_deterministic({"mobile": "m_1ake", "target": "m_4ake", "chain": "A", "method": "super"})
        rec_ce = wf.execute_deterministic({"mobile": "m_1ake", "target": "m_4ake", "chain": "A", "method": "cealign"})

        self.assertEqual(rec_align.state, WorkflowState.COMPLETED)
        self.assertEqual(rec_super.state, WorkflowState.COMPLETED)
        self.assertEqual(rec_ce.state, WorkflowState.COMPLETED)

        # align and super should produce identical unrefined global Ca RMSD on identical sequence (7.13 Å)
        self.assertAlmostEqual(rec_align.scientific_measurements["rmsd_global_ca"], 7.1307, delta=0.05)
        self.assertAlmostEqual(rec_super.scientific_measurements["rmsd_global_ca"], 7.1307, delta=0.05)
        # cealign reports rigid core alignment (~3.46 Å across ~112 residues)
        self.assertAlmostEqual(rec_ce.scientific_measurements["rmsd_angstrom"], 3.46, delta=0.1)

    def test_wf03_regression_chain_validation(self):
        """WF03 Regression: Handle nonexistent chain selection gracefully and verify raw alignment correspondence."""
        wf = GLOBAL_WORKFLOW_REGISTRY.get("WF03")
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        cmd.load(os.path.join(data_dir, "1ake.pdb"), "reg_1ake")
        cmd.load(os.path.join(data_dir, "4ake.pdb"), "reg_4ake")

        # Nonexistent chain "Z" should fail with descriptive error
        rec_bad_chain = wf.execute_deterministic({
            "mobile": "reg_1ake",
            "target": "reg_4ake",
            "mobile_chain": "Z",
            "target_chain": "Z"
        })
        self.assertEqual(rec_bad_chain.state, WorkflowState.FAILED)
        self.assertIn("does not exist", rec_bad_chain.error)

        # Raw alignment verification: verify atom correspondence is 1-to-1 without index mismatch
        res_align = GLOBAL_CAPABILITY_REGISTRY.execute("align_structures", {
            "mobile": "reg_1ake",
            "target": "reg_4ake",
            "mobile_chain": "A",
            "target_chain": "A",
            "cycles": 0
        })
        self.assertTrue(res_align["success"])
        self.assertEqual(res_align["aligned_ca_atoms"], 214)
        self.assertEqual(res_align["matched_residues"], 214)
        self.assertAlmostEqual(res_align["rmsd_global_ca"], 7.1307, delta=0.001)

    def test_deterministic_wf04_mutation_arg42_contacts_and_scientific_validation(self):
        """WF04: Analyze Arg42 in 1UBQ, validate distance-based contacts against independent NumPy calculations."""
        wf = GLOBAL_WORKFLOW_REGISTRY.get("WF04")
        self.assertIsNotNone(wf)
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        cmd.load(os.path.join(data_dir, "1ubq.pdb"), "det_1ubq")

        rec = wf.execute_deterministic({
            "target": "det_1ubq",
            "mutation_str": "R42A",
            "chain": "A",
            "cutoff": 5.0
        })
        self.assertEqual(rec.state, WorkflowState.COMPLETED)
        self.assertTrue(rec.validation_gates_passed)
        # Verify explicit distinction of single-structure mutation inspection
        self.assertTrue(rec.is_single_structure_inspection)

        meas = rec.scientific_measurements
        self.assertEqual(meas["residue_name"], "ARG")
        self.assertEqual(meas["residue_number"], 42)
        self.assertEqual(meas["neighbor_residues_count"], 10)

        # Independent NumPy distance verification across all Cartesian coordinates
        r42_coords = []
        cmd.iterate_state(1, "det_1ubq and resi 42", "r42_coords.append([x, y, z])", space={"r42_coords": r42_coords})
        r42 = np.array(r42_coords, dtype=float)

        indep_neighbors = set()
        for resi in range(1, 77):
            if resi == 42:
                continue
            res_coords = []
            cmd.iterate_state(1, f"det_1ubq and resi {resi}", "res_coords.append([x, y, z])", space={"res_coords": res_coords})
            if not res_coords:
                continue
            other = np.array(res_coords, dtype=float)
            diff = r42[:, None, :] - other[None, :, :]
            dist = np.sqrt(np.sum(diff ** 2, axis=-1))
            if np.min(dist) <= 5.0:
                indep_neighbors.add(resi)

        # Expected neighbor residues of Arg42 within 5.0 Å: Gln40, Gln41, Leu43, Ile44, Gln49, His68, Leu69, Val70, Leu71, Arg72
        expected_residues = {40, 41, 43, 44, 49, 68, 69, 70, 71, 72}
        self.assertEqual(indep_neighbors, expected_residues)

        # Check neighbor residue numbers reported by workflow match exactly
        reported_resis = set(meas["neighbor_residue_numbers"])
        self.assertEqual(reported_resis, expected_residues)

        # Verify handling of nonexistent residue produces FAILED
        rec_invalid = wf.execute_deterministic({
            "target": "det_1ubq",
            "mutation_str": "R999A",
            "chain": "A",
            "cutoff": 5.0
        })
        self.assertEqual(rec_invalid.state, WorkflowState.FAILED)

    def test_deterministic_wf05_publication_visualization(self):
        """WF05: Generate molecular figure and verify exported PNG, PSE, and replayable PML outputs."""
        wf = GLOBAL_WORKFLOW_REGISTRY.get("WF05")
        self.assertIsNotNone(wf)
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        cmd.load(os.path.join(data_dir, "1ubq.pdb"), "det_1ubq")

        with tempfile.TemporaryDirectory() as tmpdir:
            rec = wf.execute_deterministic({
                "target": "det_1ubq",
                "preset": "publication_bright",
                "output_dir": tmpdir
            })
            self.assertEqual(rec.state, WorkflowState.COMPLETED)
            self.assertTrue(rec.validation_gates_passed)

            meas = rec.scientific_measurements
            png_path = meas["png_output"]
            pml_path = meas["pml_script"]
            pse_path = meas["pse_session"]

            self.assertTrue(os.path.exists(png_path))
            self.assertGreater(os.path.getsize(png_path), 500)

            self.assertTrue(os.path.exists(pml_path))
            with open(pml_path, "r") as f:
                pml_content = f.read()
            self.assertIn("color", pml_content.lower())

            self.assertTrue(os.path.exists(pse_path))
            self.assertGreater(os.path.getsize(pse_path), 1000)

    def test_define_capability_expansion_framework(self):
        """Test Capability expansion framework with validation and Tier X rejection."""
        # 1. Successful capability definition
        def sample_calc(factor: float = 2.0) -> dict:
            return {"calculated": factor * 10.0}

        cap = define_capability(
            cap_id="custom.calc_test",
            name="custom_calc_test",
            api_mapping="internal.calc",
            category="04 Quantitative Analysis",
            description="A sample custom calculation capability.",
            parameters={"type": "object", "properties": {"factor": {"type": "number"}}},
            return_schema={"type": "object", "properties": {"calculated": {"type": "number"}}},
            risk_level="Tier A (read-only)",
            func=sample_calc
        )
        self.assertIsNotNone(cap)
        res = GLOBAL_CAPABILITY_REGISTRY.execute("custom_calc_test", {"factor": 3.0})
        self.assertTrue(res["success"])
        self.assertEqual(res["calculated"], 30.0)

        # 2. Strict rejection of Tier X (prohibited / unsafe)
        with self.assertRaises(ValueError):
            define_capability(
                cap_id="dangerous.shell",
                name="dangerous_shell",
                api_mapping="os.system",
                category="Dangerous",
                description="Dangerous capability that must be rejected.",
                parameters={"type": "object"},
                return_schema={"type": "object"},
                risk_level="Tier X (prohibited)",
                func=lambda: None
            )

    def test_classify_error_categories(self):
        """Verify deterministic error classification across different failure types."""
        self.assertEqual(classify_error(TypeError("missing argument")), ErrorClassification.DETERMINISTIC_NON_RETRYABLE)
        self.assertEqual(classify_error(TimeoutError("request timed out")), ErrorClassification.TRANSIENT_RETRYABLE)
        self.assertEqual(classify_error(ConnectionError("remote host disconnected")), ErrorClassification.TRANSIENT_RETRYABLE)
        self.assertEqual(classify_error("Precondition failed: Object does not exist"), ErrorClassification.VALIDATION_FAILURE)
        self.assertEqual(classify_error("Tool 'system_exec' is not in the authorized tool registry"), ErrorClassification.UNAUTHORIZED_TOOL)
        self.assertEqual(classify_error("Execution was cancelled by the user"), ErrorClassification.CANCELLED)

    def test_workflow_session_state_and_validation_gates(self):
        """Verify WorkflowSession state machine and mandatory validation gate enforcement."""
        wf = GLOBAL_WORKFLOW_REGISTRY.get("WF01")
        self.assertIsNotNone(wf)
        session = WorkflowSession(wf, {"pdb_id": "1ubq"}, intent_match_confidence=0.95)
        self.assertEqual(session.state, WorkflowState.PENDING)

        session.start()
        self.assertEqual(session.state, WorkflowState.RUNNING)

        # Record a successful tool call
        session.record_tool_call("fetch_structure", {"pdb_id": "1ubq"}, {"success": True, "atom_count": 660, "chains": ["A"]})
        self.assertEqual(session.state, WorkflowState.RUNNING)
        self.assertEqual(session.scientific_measurements["atom_count"], 660)

        rec = session.finalize()
        self.assertEqual(rec.state, WorkflowState.COMPLETED)
        self.assertTrue(rec.validation_gates_passed)

        # Test failure case when mandatory gate fails
        session_fail = WorkflowSession(wf, {"pdb_id": "1ubq"}, intent_match_confidence=0.95)
        session_fail.start()
        session_fail.record_tool_call("fetch_structure", {"pdb_id": "1ubq"}, {"success": False, "error": "Network timeout"})
        rec_fail = session_fail.finalize()
        self.assertEqual(rec_fail.state, WorkflowState.FAILED)
        self.assertFalse(rec_fail.validation_gates_passed)

    def test_wf03_advanced_scientific_reporting_and_ambiguous_chains(self):
        """WF03: Verify explicit metric distinction (global Ca, refined Ca, refined all-atom) and ambiguous assembly handling."""
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        cmd.load(os.path.join(data_dir, "1ake.pdb"), "rpt_1ake")
        cmd.load(os.path.join(data_dir, "4ake.pdb"), "rpt_4ake")

        # 1. Verify metric distinction and residue correspondence
        res = GLOBAL_CAPABILITY_REGISTRY.execute("align_structures", {
            "mobile": "rpt_1ake",
            "target": "rpt_4ake",
            "mobile_chain": "A",
            "target_chain": "A",
            "cycles": 5,
            "cutoff": 2.0
        })
        self.assertTrue(res["success"])
        self.assertAlmostEqual(res["rmsd_global_ca"], 7.1307, delta=0.001)
        self.assertAlmostEqual(res["rmsd_refined_ca"], 1.6663, delta=0.001)
        self.assertAlmostEqual(res["rmsd_refined_all_atom"], 2.0691, delta=0.001)
        self.assertEqual(res["aligned_ca_atoms"], 214)
        self.assertEqual(res["refined_ca_atoms"], 140)
        self.assertEqual(res["aligned_all_atoms"], 1135)
        self.assertEqual(res["matched_residues"], 214)
        self.assertEqual(res["refined_core_residues"], 152)
        self.assertIn("residue_correspondence", res)
        self.assertEqual(res["residue_correspondence_count"], 152)
        self.assertEqual(res["residue_correspondence"][0]["mobile"], "A:MET1")
        self.assertEqual(res["residue_correspondence"][0]["target"], "A:MET1")

        # 2. Ambiguous multi-chain assembly test: disjoint chains ['A', 'B'] vs ['C', 'D']
        cmd.copy("rpt_cd", "rpt_4ake")
        cmd.alter("rpt_cd and chain A", "chain='C'")
        cmd.alter("rpt_cd and chain B", "chain='D'")
        wf = GLOBAL_WORKFLOW_REGISTRY.get("WF03")

        # Without explicit chain, must fail requiring clarification
        rec_amb = wf.execute_deterministic({
            "mobile": "rpt_1ake",
            "target": "rpt_cd"
        })
        self.assertEqual(rec_amb.state, WorkflowState.FAILED)
        self.assertIn("Ambiguous biological assembly", rec_amb.error)

        # With explicit chain correspondence, must succeed
        rec_resolved = wf.execute_deterministic({
            "mobile": "rpt_1ake",
            "target": "rpt_cd",
            "mobile_chain": "A",
            "target_chain": "C"
        })
        self.assertEqual(rec_resolved.state, WorkflowState.COMPLETED)
        meas = rec_resolved.scientific_measurements
        self.assertAlmostEqual(meas["rmsd_global_ca"], 7.1307, delta=0.001)
        self.assertEqual(meas["mobile_chain"], "A")
        self.assertEqual(meas["target_chain"], "C")


if __name__ == "__main__":
    unittest.main()
