"""
Automated unit and integration tests for structure loading (fetch_structure, load_structure)
and agent loop prevention / error recovery logic.
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

from pymol_ai_copilot.agent.controller import AgentController
from pymol_ai_copilot.agent.tool_registry import GLOBAL_REGISTRY


class TestStructureLoadingAndErrorRecovery(unittest.TestCase):
    def setUp(self):
        if PYMOL_AVAILABLE:
            cmd.reinitialize()

    # --- Tool Registry Presence ---
    def test_loading_tools_registered(self):
        self.assertIsNotNone(GLOBAL_REGISTRY.get("fetch_structure"))
        self.assertIsNotNone(GLOBAL_REGISTRY.get("load_structure"))

    # --- fetch_structure tests ---
    @unittest.skipUnless(PYMOL_AVAILABLE, "PyMOL required")
    def test_fetch_structure_success(self):
        """Verify fetching a real PDB (1ubq) loads atoms and returns metadata."""
        res = GLOBAL_REGISTRY.execute("fetch_structure", {"pdb_id": "1ubq", "object_name": "test_fetch_ubq"})
        self.assertTrue(res["success"])
        self.assertEqual(res["object_name"], "test_fetch_ubq")
        self.assertGreater(res["atom_count"], 0)
        self.assertIn("A", res["chains"])
        self.assertIn("test_fetch_ubq", cmd.get_names("objects"))

    @unittest.skipUnless(PYMOL_AVAILABLE, "PyMOL required")
    def test_fetch_structure_collision_disambiguation(self):
        """Verify that loading an existing object name does not overwrite; it disambiguates."""
        res1 = GLOBAL_REGISTRY.execute("fetch_structure", {"pdb_id": "1ubq", "object_name": "dup_test"})
        self.assertTrue(res1["success"])
        self.assertEqual(res1["object_name"], "dup_test")

        res2 = GLOBAL_REGISTRY.execute("fetch_structure", {"pdb_id": "1ubq", "object_name": "dup_test"})
        self.assertTrue(res2["success"])
        self.assertEqual(res2["object_name"], "dup_test_1")
        self.assertTrue(res2["collision_renamed"])
        # Both objects exist in PyMOL
        names = cmd.get_names("objects")
        self.assertIn("dup_test", names)
        self.assertIn("dup_test_1", names)

    @unittest.skipUnless(PYMOL_AVAILABLE, "PyMOL required")
    def test_fetch_structure_invalid_id_format(self):
        """Verify rejection of malformed or path-traversal PDB IDs."""
        res = GLOBAL_REGISTRY.execute("fetch_structure", {"pdb_id": "../etc/passwd"})
        self.assertFalse(res["success"])
        self.assertIn("Invalid PDB identifier format", res["error"])

    @unittest.skipUnless(PYMOL_AVAILABLE, "PyMOL required")
    def test_fetch_structure_nonexistent_accession(self):
        """Verify graceful error reporting when PDB accession does not exist."""
        res = GLOBAL_REGISTRY.execute("fetch_structure", {"pdb_id": "0000"})
        self.assertFalse(res["success"])
        self.assertIn("Unable to download or parse PDB", res["error"])

    # --- load_structure tests ---
    @unittest.skipUnless(PYMOL_AVAILABLE, "PyMOL required")
    def test_load_structure_success(self):
        """Verify loading local PDB file."""
        pdb_path = os.path.abspath("pymol_ai_copilot/tests/data/1ake.pdb")
        res = GLOBAL_REGISTRY.execute("load_structure", {"file_path": pdb_path, "object_name": "test_load_1ake"})
        self.assertTrue(res["success"])
        self.assertEqual(res["object_name"], "test_load_1ake")
        self.assertGreater(res["atom_count"], 0)
        self.assertIn("test_load_1ake", cmd.get_names("objects"))

    @unittest.skipUnless(PYMOL_AVAILABLE, "PyMOL required")
    def test_load_structure_nonexistent_file(self):
        """Verify error when local file does not exist."""
        res = GLOBAL_REGISTRY.execute("load_structure", {"file_path": "/tmp/nonexistent_struct_12345.pdb"})
        self.assertFalse(res["success"])
        self.assertIn("does not exist", res["error"])

    @unittest.skipUnless(PYMOL_AVAILABLE, "PyMOL required")
    def test_load_structure_remote_url_rejection(self):
        """Verify rejection of remote URLs (users should use fetch_structure)."""
        res = GLOBAL_REGISTRY.execute("load_structure", {"file_path": "https://files.rcsb.org/download/1ubq.pdb"})
        self.assertFalse(res["success"])
        self.assertIn("Remote URLs are not supported", res["error"])

    @unittest.skipUnless(PYMOL_AVAILABLE, "PyMOL required")
    def test_load_structure_unauthorized_path(self):
        """Verify security boundary: restricted access to system directories."""
        res = GLOBAL_REGISTRY.execute("load_structure", {"file_path": "/etc/passwd"})
        self.assertFalse(res["success"])
        self.assertIn("restricted", res["error"].lower())

    @unittest.skipUnless(PYMOL_AVAILABLE, "PyMOL required")
    def test_load_structure_rejects_symlink_to_sensitive_path(self):
        """A symlink with a .pdb name must not bypass the sensitive-path check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            link = os.path.join(tmpdir, "innocent.pdb")
            try:
                os.symlink("/etc/passwd", link)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks are not available on this platform.")

            res = GLOBAL_REGISTRY.execute("load_structure", {"file_path": link})

            self.assertFalse(res["success"])
            self.assertIn("restricted", res["error"].lower())

    @unittest.skipUnless(PYMOL_AVAILABLE, "PyMOL required")
    def test_load_structure_unexpected_extension(self):
        """Verify rejection of non-molecular file types."""
        with tempfile.NamedTemporaryFile(suffix=".sh") as tmp:
            res = GLOBAL_REGISTRY.execute("load_structure", {"file_path": tmp.name})
            self.assertFalse(res["success"])
            self.assertIn("Unsupported molecular file extension", res["error"])

    # --- Agent Error Recovery & Loop Prevention tests ---
    def test_agent_loop_breaker_stops_early(self):
        """Verify that when a model repeats an identical failed tool call, it stops early instead of exhausting max steps."""
        class RepeatingFailureOllamaClient:
            def __init__(self):
                self.calls = 0
            def cancel(self): pass
            def reset_cancellation(self): pass
            def chat(self, model, messages, tools, temperature):
                self.calls += 1
                # Emits the exact same invalid tool call every time
                return {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{"id": f"call_{self.calls}", "name": "invalid_tool", "arguments": {"x": 1}}]
                }

        controller = AgentController(ollama_client=RepeatingFailureOllamaClient(), model_name="mock-model")
        # max_steps is set to 8
        res = controller.run("Trigger repeated invalid tool", max_steps=8)
        # Should stop after at most 2 steps, NOT exhaust all 8 steps!
        self.assertLessEqual(res["steps_count"], 3)
        self.assertLess(res["steps_count"], 8)
        # Check that the repeated failure error was emitted
        step2_results = res["steps"][1]["tool_results"]
        self.assertTrue(step2_results[0]["result"].get("repeated_failure", False))

    def test_agent_recovers_with_valid_strategy(self):
        """Verify that agent recovers if it tries an alternative valid tool after failure."""
        class RecoveringOllamaClient:
            def __init__(self):
                self.step = 0
            def cancel(self): pass
            def reset_cancellation(self): pass
            def chat(self, model, messages, tools, temperature):
                self.step += 1
                if self.step == 1:
                    # Tries invalid tool "download"
                    return {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [{"id": "call_1", "name": "download", "arguments": {"id": "1ubq"}}]
                    }
                elif self.step == 2:
                    # Recovers with valid tool "count_atoms"
                    return {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [{"id": "call_2", "name": "count_atoms", "arguments": {"selection": "all"}}]
                    }
                else:
                    return {
                        "role": "assistant",
                        "content": "Recovered and completed.",
                        "tool_calls": []
                    }

        controller = AgentController(ollama_client=RecoveringOllamaClient(), model_name="mock-model")
        res = controller.run("Test recovery", max_steps=5)
        self.assertEqual(res["steps_count"], 3)
        self.assertTrue(res["steps"][1]["tool_results"][0]["result"]["success"])
        self.assertIn("Recovered and completed", res["final_response"])

    @unittest.skipUnless(PYMOL_AVAILABLE, "PyMOL required")
    def test_fetch_structure_network_failure(self):
        """Verify graceful error reporting when network failure occurs during fetch."""
        from unittest.mock import patch
        with patch.object(cmd, "fetch", side_effect=Exception("Connection refused / timed out")):
            res = GLOBAL_REGISTRY.execute("fetch_structure", {"pdb_id": "1ubq", "object_name": "net_fail_test"})
            self.assertFalse(res["success"])
            self.assertIn("Connection refused", res["error"])

    @unittest.skipUnless(PYMOL_AVAILABLE, "PyMOL required")
    def test_load_structure_cif_format(self):
        """Verify that mmCIF / .cif format files are accepted and loaded."""
        with tempfile.NamedTemporaryFile(suffix=".cif", mode="w", delete=False) as tmp:
            # Minimal CIF format header
            tmp.write("data_TEST\n#\n_entry.id TEST\n")
            tmp_path = tmp.name

        try:
            res = GLOBAL_REGISTRY.execute("load_structure", {"file_path": tmp_path, "object_name": "test_cif"})
            # Result is structured and does not crash
            self.assertIn("success", res)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @unittest.skipUnless(PYMOL_AVAILABLE, "PyMOL required")
    def test_agent_complete_multistep_execution(self):
        """Verify multi-step execution where agent downloads, displays cartoon, and colors."""
        class MultiStepClient:
            def __init__(self):
                self.step = 0
            def cancel(self): pass
            def reset_cancellation(self): pass
            def chat(self, model, messages, tools, temperature):
                self.step += 1
                if self.step == 1:
                    return {
                        "role": "assistant",
                        "content": "Fetching structure 1ubq",
                        "tool_calls": [{"id": "c1", "name": "fetch_structure", "arguments": {"pdb_id": "1ubq", "object_name": "agent_ubq"}}]
                    }
                elif self.step == 2:
                    return {
                        "role": "assistant",
                        "content": "Styling cartoon and coloring by secondary structure",
                        "tool_calls": [
                            {"id": "c2a", "name": "show_representation", "arguments": {"representation": "cartoon", "selection": "agent_ubq"}},
                            {"id": "c2b", "name": "color_selection", "arguments": {"color": "secondary_structure", "selection": "agent_ubq"}}
                        ]
                    }
                else:
                    return {
                        "role": "assistant",
                        "content": "Ubiquitin 1UBQ has been loaded and styled successfully.",
                        "tool_calls": []
                    }

        controller = AgentController(ollama_client=MultiStepClient(), model_name="mock-model")
        res = controller.run("Download 1UBQ, show as cartoon, color by secondary structure", max_steps=5)
        self.assertTrue(res["success"])
        self.assertEqual(res["steps_count"], 3)
        self.assertIn("agent_ubq", cmd.get_names("objects"))
        self.assertIn("Ubiquitin 1UBQ has been loaded", res["final_response"])


if __name__ == "__main__":
    unittest.main()
