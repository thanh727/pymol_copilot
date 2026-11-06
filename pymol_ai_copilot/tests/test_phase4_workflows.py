"""
Phase 4: Advanced Structural Biology Workflows — Scientific Validation Test Suite.

Validates:
1. Ligand Interaction Analysis (WF06): identification, alternate conformation handling,
   minimum heavy-atom distances, polar contact candidates, independent NumPy validation.
2. Solvent Accessibility Analysis (WF07): absolute SASA (Å²), relative accessibility (RSA %),
   per-residue breakdown, Tien et al. (2013) MaxSASA references, B-factor mapping.
3. Epitope Structural Mapping (WF08): linear peptide sequence search, residue range mapping,
   spatial centroid and diameter clustering in NumPy, surface accessibility.
4. WT-Mutant Structural Comparison (WF09): sequence-aware alignment, local C-alpha displacement,
   contact network deltas, non-fabrication of coordinates.
5. Batch Structural Analysis (WF10): multi-structure alignment, consistent metrics table,
   CSV, JSON, PNG, and PSE exports, safety limits.
6. Bilingual Natural Language Intent Matching & Deterministic Execution Gates.
"""

import os
import shutil
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

from pymol_ai_copilot.agent.capability_registry import GLOBAL_CAPABILITY_REGISTRY
from pymol_ai_copilot.agent.workflow_engine import (
    GLOBAL_WORKFLOW_REGISTRY,
    WorkflowState
)


class TestPhase4AdvancedWorkflows(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not PYMOL_AVAILABLE:
            raise unittest.SkipTest("PyMOL is not available.")
        cls.data_dir = os.path.join(os.path.dirname(__file__), "data")
        cls.tmpdir = tempfile.mkdtemp(prefix="phase4_val_")

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.tmpdir):
            shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def setUp(self):
        cmd.reinitialize()
        # Load representative validation dataset
        cmd.load(os.path.join(self.data_dir, "1ubq.pdb"), "p4_1ubq")
        cmd.load(os.path.join(self.data_dir, "1ake.pdb"), "p4_1ake")
        cmd.load(os.path.join(self.data_dir, "4ake.pdb"), "p4_4ake")
        cmd.load(os.path.join(self.data_dir, "1ubq_r42a.pdb"), "p4_r42a")

    # ========================================================================
    # Task 2: Ligand Interaction Analysis (WF06)
    # ========================================================================

    def test_ligand_identification_and_additive_filtering(self):
        """WF06: Verify identification of true ligand (AP5) and exclusion of solvent/additives."""
        res = GLOBAL_CAPABILITY_REGISTRY.execute("identify_ligands", {"object_name": "p4_1ake"})
        self.assertTrue(res["success"])
        self.assertEqual(res["total_ligands"], 2)  # AP5 in chain A and chain B
        lig_names = [lig["resn"] for lig in res["ligands"]]
        self.assertIn("AP5", lig_names)
        # Verify HOH is excluded as solvent
        excluded_reasons = [e["reason"] for e in res["excluded_additives"]]
        self.assertIn("solvent", excluded_reasons)

    def test_ligand_interactions_and_independent_numpy_distances(self):
        """WF06: Analyze AP5 contacts, handle altlocs, and independently verify distances via NumPy."""
        res = GLOBAL_CAPABILITY_REGISTRY.execute("analyze_ligand_interactions", {
            "object_name": "p4_1ake",
            "ligand_resn": "AP5",
            "ligand_resi": "215",
            "ligand_chain": "A",
            "cutoff": 4.0,
            "altloc": "A"
        })
        self.assertTrue(res["success"])
        self.assertGreater(res["contacting_residues_count"], 0)
        self.assertGreater(res["polar_contacts_count"], 0)
        self.assertIn("scientific_limitation", res)

        # Independent NumPy verification for key contact residues
        # 1. Extract AP5 heavy atom coordinates (altloc A)
        lig_coords = []
        cmd.iterate_state(1, "p4_1ake and chain A and resi 215 and resn AP5 and (alt ''+A) and not elem H",
                          "lig_coords.append((x, y, z))", space={"lig_coords": lig_coords})
        lig_arr = np.array(lig_coords, dtype=float)

        # 2. Extract Thr15 heavy atom coordinates
        thr15_coords = []
        cmd.iterate_state(1, "p4_1ake and chain A and resi 15 and (alt ''+A) and not elem H",
                          "thr15_coords.append((x, y, z))", space={"thr15_coords": thr15_coords})
        thr15_arr = np.array(thr15_coords, dtype=float)

        # Pairwise distance matrix
        pw_dists = np.linalg.norm(thr15_arr[:, None, :] - lig_arr[None, :, :], axis=-1)
        ref_min_dist = round(float(np.min(pw_dists)), 3)

        # Find Thr15 in tool results
        t15_tool = next((c for c in res["contacts"] if c["residue_number"] == "15"), None)
        self.assertIsNotNone(t15_tool)
        self.assertAlmostEqual(t15_tool["min_distance_angstrom"], ref_min_dist, delta=0.001)

    def test_ligand_visualization_and_export(self):
        """WF06: Verify pocket visualization setup and CSV/JSON export."""
        res_vis = GLOBAL_CAPABILITY_REGISTRY.execute("visualize_ligand_pocket", {
            "object_name": "p4_1ake",
            "ligand_resn": "AP5",
            "ligand_resi": "215",
            "ligand_chain": "A",
            "cutoff": 4.0,
            "show_contacts": True
        })
        self.assertTrue(res_vis["success"])

        csv_out = os.path.join(self.tmpdir, "ap5_contacts.csv")
        res_exp = GLOBAL_CAPABILITY_REGISTRY.execute("export_ligand_contacts", {
            "object_name": "p4_1ake",
            "ligand_resn": "AP5",
            "ligand_resi": "215",
            "output_path": csv_out,
            "format": "csv"
        })
        self.assertTrue(res_exp["success"])
        self.assertTrue(os.path.exists(csv_out))
        self.assertGreater(os.path.getsize(csv_out), 100)

    def test_deterministic_wf06_execution(self):
        """WF06: Execute full deterministic workflow and verify gates."""
        wf = GLOBAL_WORKFLOW_REGISTRY.get("WF06")
        self.assertIsNotNone(wf)
        rec = wf.execute_deterministic({
            "target": "p4_1ake",
            "ligand_resn": "AP5",
            "ligand_chain": "A",
            "cutoff": 4.0
        })
        self.assertEqual(rec.state, WorkflowState.COMPLETED)
        self.assertTrue(rec.validation_gates_passed)
        meas = rec.scientific_measurements
        self.assertEqual(meas["ligand_resn"], "AP5")
        self.assertGreater(meas["contacting_residues_count"], 0)

    # ========================================================================
    # Task 3: Solvent Accessibility Analysis (WF07)
    # ========================================================================

    def test_sasa_calculation_and_relative_accessibility(self):
        """WF07: Calculate absolute SASA (Å²) and RSA (%), verifying buried vs exposed residues."""
        res = GLOBAL_CAPABILITY_REGISTRY.execute("calculate_sasa", {
            "object_name": "p4_1ubq",
            "probe_radius": 1.4,
            "dot_density": 2
        })
        self.assertTrue(res["success"])
        self.assertAlmostEqual(res["total_sasa_angstrom2"], 4861.86, delta=50.0)
        self.assertEqual(res["residues_analyzed"], 76)

        # Independent verification of residue accessibility
        res_map = {r["residue_number"]: r for r in res["residues"]}

        # Ile3 is in hydrophobic core -> must be buried (RSA < 20%)
        ile3 = res_map.get("3")
        self.assertIsNotNone(ile3)
        self.assertEqual(ile3["classification"], "buried")
        self.assertLess(ile3["rsa_percent"], 20.0)

        # Gln2 is surface exposed -> RSA >= 20%
        gln2 = res_map.get("2")
        self.assertIsNotNone(gln2)
        self.assertGreaterEqual(gln2["rsa_percent"], 20.0)

    def test_sasa_mapping_and_structure_comparison(self):
        """WF07: Map SASA to B-factors and compare accessibility between open (4AKE) and closed (1AKE)."""
        res_map = GLOBAL_CAPABILITY_REGISTRY.execute("map_sasa_to_structure", {
            "object_name": "p4_1ubq",
            "palette": "blue_white_red",
            "representation": "surface"
        })
        self.assertTrue(res_map["success"])

        res_comp = GLOBAL_CAPABILITY_REGISTRY.execute("compare_sasa", {
            "object1": "p4_1ake",
            "object2": "p4_4ake",
            "chain1": "A",
            "chain2": "A",
            "probe_radius": 1.4
        })
        self.assertTrue(res_comp["success"])
        self.assertEqual(res_comp["residues_compared"], 214)
        self.assertIn("significant_changes_count", res_comp)

    def test_deterministic_wf07_execution(self):
        """WF07: Execute full deterministic solvent accessibility workflow."""
        wf = GLOBAL_WORKFLOW_REGISTRY.get("WF07")
        self.assertIsNotNone(wf)
        rec = wf.execute_deterministic({
            "target": "p4_1ubq",
            "probe_radius": 1.4
        })
        self.assertEqual(rec.state, WorkflowState.COMPLETED)
        self.assertTrue(rec.validation_gates_passed)
        meas = rec.scientific_measurements
        self.assertGreater(meas["total_sasa_angstrom2"], 4000.0)
        self.assertGreater(meas["buried_residues_count"], 0)
        self.assertGreater(meas["exposed_residues_count"], 0)

    # ========================================================================
    # Task 4: Epitope Structural Mapping (WF08)
    # ========================================================================

    def test_epitope_sequence_mapping_and_clustering(self):
        """WF08: Map linear peptide 'TITLEVE' to 1UBQ, independently verify centroid and span."""
        res = GLOBAL_CAPABILITY_REGISTRY.execute("map_epitope_sequence", {
            "object_name": "p4_1ubq",
            "epitope_sequence": "TITLEVE"
        })
        self.assertTrue(res["success"])
        self.assertEqual(res["chain"], "A")
        self.assertEqual(res["mapped_residues_count"], 7)
        self.assertEqual(res["residue_numbers"], ["12", "13", "14", "15", "16", "17", "18"])
        self.assertTrue(res["is_spatially_clustered"])

        # Independent NumPy verification of spatial centroid
        ca_coords = []
        cmd.iterate_state(1, "p4_1ubq and chain A and resi 12-18 and name CA",
                          "ca_coords.append((x, y, z))", space={"ca_coords": ca_coords})
        ca_arr = np.array(ca_coords, dtype=float)
        indep_centroid = np.mean(ca_arr, axis=0)

        for dim in range(3):
            self.assertAlmostEqual(res["spatial_centroid"][dim], indep_centroid[dim], delta=0.001)

    def test_epitope_residue_list_mapping_and_visualization(self):
        """WF08: Map epitope via residue range '12-18' and verify publication visualization."""
        res_list = GLOBAL_CAPABILITY_REGISTRY.execute("map_epitope_sequence", {
            "object_name": "p4_1ubq",
            "residue_list": "12-18",
            "chain": "A"
        })
        self.assertTrue(res_list["success"])
        self.assertEqual(res_list["mapped_residues_count"], 7)

        res_vis = GLOBAL_CAPABILITY_REGISTRY.execute("visualize_epitope", {
            "object_name": "p4_1ubq",
            "chain": "A",
            "residue_numbers": ["12", "13", "14", "15", "16", "17", "18"],
            "representation": "surface_highlight"
        })
        self.assertTrue(res_vis["success"])

    def test_deterministic_wf08_execution(self):
        """WF08: Execute full deterministic epitope mapping workflow."""
        wf = GLOBAL_WORKFLOW_REGISTRY.get("WF08")
        self.assertIsNotNone(wf)
        rec = wf.execute_deterministic({
            "target": "p4_1ubq",
            "epitope_sequence": "TITLEVE"
        })
        self.assertEqual(rec.state, WorkflowState.COMPLETED)
        self.assertTrue(rec.validation_gates_passed)
        meas = rec.scientific_measurements
        self.assertEqual(meas["mapped_residues_count"], 7)
        self.assertTrue(meas["is_spatially_clustered"])

    # ========================================================================
    # Task 5: WT–Mutant Structural Comparison (WF09)
    # ========================================================================

    def test_compare_wt_mutant_structures(self):
        """WF09: Compare 1UBQ WT (Arg42) vs 1UBQ R42A mutant, verifying local displacement and contact deltas."""
        res = GLOBAL_CAPABILITY_REGISTRY.execute("compare_wt_mutant", {
            "wildtype_object": "p4_1ubq",
            "mutant_object": "p4_r42a",
            "mutation_str": "R42A",
            "chain": "A",
            "radius": 5.0
        })
        self.assertTrue(res["success"])
        self.assertAlmostEqual(res["global_chain_rmsd_angstrom"], 0.0, delta=0.01)

        loc = res["local_mutation_comparison"]
        self.assertIsNotNone(loc)
        self.assertEqual(loc["wildtype_residue"], "ARG")
        self.assertEqual(loc["mutant_residue"], "ALA")
        self.assertAlmostEqual(loc["ca_displacement_angstrom"], 0.0, delta=0.001)
        self.assertIn("scientific_limitation", res)
        # Verify non-fabrication of coordinates: mutant ALA has 5 atoms, WT ARG has 11
        wt_atoms = cmd.count_atoms("p4_1ubq and chain A and resi 42")
        mut_atoms = cmd.count_atoms("p4_r42a and chain A and resi 42")
        self.assertEqual(wt_atoms, 11)
        self.assertEqual(mut_atoms, 5)

    def test_deterministic_wf09_execution(self):
        """WF09: Execute full deterministic WT-mutant structural comparison workflow."""
        wf = GLOBAL_WORKFLOW_REGISTRY.get("WF09")
        self.assertIsNotNone(wf)
        rec = wf.execute_deterministic({
            "wildtype_object": "p4_1ubq",
            "mutant_object": "p4_r42a",
            "mutation_str": "R42A",
            "chain": "A"
        })
        self.assertEqual(rec.state, WorkflowState.COMPLETED)
        self.assertTrue(rec.validation_gates_passed)
        meas = rec.scientific_measurements
        self.assertEqual(meas["mutation"], "R42A")
        self.assertAlmostEqual(meas["ca_displacement_angstrom"], 0.0, delta=0.001)

    # ========================================================================
    # Task 6: Batch Structural Analysis (WF10)
    # ========================================================================

    def test_batch_compare_structures_and_exports(self):
        """WF10: Batch align multiple structures against reference, verify exports and safety limits."""
        res = GLOBAL_CAPABILITY_REGISTRY.execute("batch_compare_structures", {
            "structure_names": ["p4_1ake", "p4_4ake"],
            "reference_name": "p4_4ake",
            "chain": "A",
            "method": "align",
            "output_dir": self.tmpdir
        })
        self.assertTrue(res["success"])
        self.assertEqual(res["total_structures_analyzed"], 2)
        self.assertEqual(res["comparisons_count"], 1)

        r0 = res["results"][0]
        self.assertEqual(r0["structure"], "p4_1ake")
        self.assertEqual(r0["reference"], "p4_4ake")
        self.assertAlmostEqual(r0["rmsd_global_ca"], 7.1307, delta=0.001)
        self.assertAlmostEqual(r0["rmsd_refined_all_atom"], 2.0691, delta=0.001)

        # Verify exported files exist
        exp = res["exported_files"]
        self.assertTrue(os.path.exists(exp["csv"]))
        self.assertTrue(os.path.exists(exp["json"]))
        self.assertTrue(os.path.exists(exp["png"]))
        self.assertTrue(os.path.exists(exp["pse"]))

        # Verify batch size safety limit (>20 structures rejected)
        fake_names = [f"struct_{i}" for i in range(25)]
        res_limit = GLOBAL_CAPABILITY_REGISTRY.execute("batch_compare_structures", {
            "structure_names": fake_names
        })
        self.assertFalse(res_limit["success"])

    def test_deterministic_wf10_execution(self):
        """WF10: Execute full deterministic batch structural comparison workflow."""
        wf = GLOBAL_WORKFLOW_REGISTRY.get("WF10")
        self.assertIsNotNone(wf)
        rec = wf.execute_deterministic({
            "structure_names": ["p4_1ake", "p4_4ake"],
            "reference_name": "p4_4ake",
            "chain": "A",
            "output_dir": self.tmpdir
        })
        self.assertEqual(rec.state, WorkflowState.COMPLETED)
        self.assertTrue(rec.validation_gates_passed)
        meas = rec.scientific_measurements
        self.assertEqual(meas["comparisons_count"], 1)

    def test_identify_mutations_with_residue_parameter(self):
        """Regression: identify_mutations must pass chain/resi to the correct keyword arguments."""
        res = GLOBAL_CAPABILITY_REGISTRY.execute("identify_mutations", {
            "wildtype_object": "p4_1ubq",
            "mutant_object": "p4_r42a",
            "chain": "A",
            "resi": "42"
        })
        self.assertTrue(res["success"])
        local = res["local_mutation_comparison"]
        self.assertIsNotNone(local)
        self.assertEqual(local["wildtype_residue"], "ARG")
        self.assertEqual(local["mutant_residue"], "ALA")
        self.assertAlmostEqual(local["ca_displacement_angstrom"], 0.0, delta=0.001)

    # ========================================================================
    # Task 7: Natural Language Intent Matching & Entity Extraction
    # ========================================================================

    def test_bilingual_intent_matching_phase4_workflows(self):
        """Verify bilingual NLP matching for Phase 4 workflows (English and Vietnamese)."""
        reg = GLOBAL_WORKFLOW_REGISTRY

        # WF06: Ligand
        wf6_en, _, conf6_en = reg.match_workflow("Analyze ligand AP5 binding pocket in 1ake")
        self.assertEqual(wf6_en.workflow_id, "WF06")
        wf6_vi, _, conf6_vi = reg.match_workflow("Phân tích túi gắn của chất gắn AP5")
        self.assertEqual(wf6_vi.workflow_id, "WF06")

        # WF07: SASA
        wf7_en, _, conf7_en = reg.match_workflow("Calculate solvent accessibility SASA for 1ubq")
        self.assertEqual(wf7_en.workflow_id, "WF07")
        wf7_vi, _, conf7_vi = reg.match_workflow("Tính diện tích tiếp xúc dung môi SASA của protein")
        self.assertEqual(wf7_vi.workflow_id, "WF07")

        # WF08: Epitope
        wf8_en, _, conf8_en = reg.match_workflow("Map epitope sequence TITLEVE on 1ubq")
        self.assertEqual(wf8_en.workflow_id, "WF08")
        wf8_vi, _, conf8_vi = reg.match_workflow("Ánh xạ đoạn epitope TITLEVE lên cấu trúc")
        self.assertEqual(wf8_vi.workflow_id, "WF08")

        # WF09: WT-Mutant
        wf9_en, _, conf9_en = reg.match_workflow("Compare wt and mutant structures for mutation R42A")
        self.assertEqual(wf9_en.workflow_id, "WF09")
        wf9_vi, _, conf9_vi = reg.match_workflow("So sánh cấu trúc đột biến R42A với wildtype")
        self.assertEqual(wf9_vi.workflow_id, "WF09")

        # WF10: Batch
        wf10_en, _, conf10_en = reg.match_workflow("Batch compare multiple structures")
        self.assertEqual(wf10_en.workflow_id, "WF10")
        wf10_vi, _, conf10_vi = reg.match_workflow("So sánh hàng loạt các cấu trúc protein")
        self.assertEqual(wf10_vi.workflow_id, "WF10")


if __name__ == "__main__":
    unittest.main()

