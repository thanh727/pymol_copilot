"""
Live Acceptance Testing with local Ollama models.
Tests the 3 user scenarios:
1. "Download PDB 1UBQ, display it as cartoon, color by secondary structure, and orient the protein."
2. "Download 1AKE and identify residues within 5 angstroms of its ligand."
3. "Tải về cấu trúc 1ubq và hiển thị dạng cartoon."
"""

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
from pymol_ai_copilot.agent.ollama_client import OllamaClient


class TestLiveOllamaAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Verify Ollama is reachable
        client = OllamaClient()
        ok, msg = client.check_connection()
        if not ok:
            raise unittest.SkipTest(f"Ollama service not available: {msg}")
        models = client.list_models()
        model_names = [m.get("name") for m in models]
        cls.has_qwen = any("qwen2.5-coder:7b" in m for m in model_names)
        if not cls.has_qwen:
            raise unittest.SkipTest("qwen2.5-coder:7b not found in Ollama")

    def setUp(self):
        if PYMOL_AVAILABLE:
            cmd.reinitialize()

    def test_live_workflow_1ubq_styling(self):
        """Test: Download PDB 1UBQ, display it as cartoon, color by secondary structure, and orient the protein."""
        controller = AgentController(model_name="qwen2.5-coder:7b")
        prompt = "Download PDB 1UBQ, display it as cartoon, color by secondary structure, and orient the protein."
        res = controller.run(prompt, max_steps=6)

        print("\n--- Live Test 1: 1UBQ Styling ---")
        print(f"Steps count: {res['steps_count']}")
        for s in res["steps"]:
            tc_names = [tc["name"] for tc in s["tool_calls"]]
            print(f"  Step {s['step']}: tools called = {tc_names}")
            for tr in s["tool_results"]:
                print(f"    Tool: {tr['tool']}, success: {tr['result'].get('success')}")

        print(f"Final response: {res['final_response']}")
        print(f"Objects in PyMOL: {cmd.get_names('objects')}")

        # Assertions
        self.assertTrue(res["success"])
        # Object '1ubq' or similar should be loaded
        objects = cmd.get_names("objects")
        self.assertTrue(any("1ubq" in obj.lower() for obj in objects), f"Expected 1ubq in {objects}")
        # At least one step called fetch_structure
        all_called_tools = [tr["tool"] for s in res["steps"] for tr in s["tool_results"]]
        self.assertIn("fetch_structure", all_called_tools)
        # Should not exhaust steps repeating identical calls
        self.assertLessEqual(res["steps_count"], 5)

    def test_live_workflow_1ake_ligand_neighborhood(self):
        """Test: Download 1AKE and identify residues within 5 angstroms of its ligand."""
        controller = AgentController(model_name="qwen2.5-coder:7b")
        prompt = "Download 1AKE and identify residues within 5 angstroms of its ligand."
        res = controller.run(prompt, max_steps=6)

        print("\n--- Live Test 2: 1AKE Ligand Binding Site ---")
        print(f"Steps count: {res['steps_count']}")
        for s in res["steps"]:
            tc_names = [tc["name"] for tc in s["tool_calls"]]
            print(f"  Step {s['step']}: tools called = {tc_names}")
            for tr in s["tool_results"]:
                print(f"    Tool: {tr['tool']}, success: {tr['result'].get('success')}")

        print(f"Final response: {res['final_response']}")
        print(f"Objects in PyMOL: {cmd.get_names('objects')}")

        self.assertTrue(res["success"])
        objects = cmd.get_names("objects")
        self.assertTrue(any("1ake" in obj.lower() for obj in objects), f"Expected 1ake in {objects}")
        all_called_tools = [tr["tool"] for s in res["steps"] for tr in s["tool_results"]]
        self.assertIn("fetch_structure", all_called_tools)
        self.assertLessEqual(res["steps_count"], 6)

    def test_live_workflow_vietnamese_fetch_and_cartoon(self):
        """Test: Tải về cấu trúc 1ubq và hiển thị dạng cartoon."""
        controller = AgentController(model_name="qwen2.5-coder:7b")
        prompt = "Tải về cấu trúc 1ubq và hiển thị dạng cartoon."
        res = controller.run(prompt, max_steps=5)

        print("\n--- Live Test 3: Vietnamese Prompt ---")
        print(f"Steps count: {res['steps_count']}")
        for s in res["steps"]:
            tc_names = [tc["name"] for tc in s["tool_calls"]]
            print(f"  Step {s['step']}: tools called = {tc_names}")
            for tr in s["tool_results"]:
                print(f"    Tool: {tr['tool']}, success: {tr['result'].get('success')}")

        print(f"Final response: {res['final_response']}")
        print(f"Objects in PyMOL: {cmd.get_names('objects')}")

        self.assertTrue(res["success"])
        objects = cmd.get_names("objects")
        self.assertTrue(any("1ubq" in obj.lower() for obj in objects), f"Expected 1ubq in {objects}")
        all_called_tools = [tr["tool"] for s in res["steps"] for tr in s["tool_results"]]
        self.assertIn("fetch_structure", all_called_tools)
        self.assertLessEqual(res["steps_count"], 5)


if __name__ == "__main__":
    unittest.main()
