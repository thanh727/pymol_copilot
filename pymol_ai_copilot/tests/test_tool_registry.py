"""
Unit tests for ToolRegistry and Ollama schema generation.
"""

import unittest
from pymol_ai_copilot.agent.tool_registry import GLOBAL_REGISTRY, ToolDefinition, ToolRegistry


class TestToolRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = GLOBAL_REGISTRY

    def test_registered_tools_count(self):
        tools = self.registry.list_tools()
        self.assertGreaterEqual(len(tools), 20)

    def test_expected_tools_present(self):
        expected = [
            "fetch_structure", "load_structure",
            "list_objects", "get_object_info", "get_chains", "get_residues",
            "count_atoms", "get_structure_summary", "show_representation",
            "hide_representation", "color_selection", "select_residues",
            "highlight_residues", "align_structures", "calculate_rmsd",
            "compare_residues", "identify_mutations", "calculate_distances",
            "find_nearby_residues", "find_polar_contact_candidates",
            "inspect_binding_pocket", "analyze_mutation", "export_png",
            "save_session", "export_pml"
        ]
        for name in expected:
            self.assertIsNotNone(self.registry.get(name), f"Tool {name} should be registered.")

    def test_ollama_format_schema(self):
        ollama_tools = self.registry.get_ollama_tools()
        self.assertIsInstance(ollama_tools, list)
        for t in ollama_tools:
            self.assertEqual(t.get("type"), "function")
            func = t.get("function", {})
            self.assertIn("name", func)
            self.assertIn("description", func)
            self.assertIn("parameters", func)

    def test_unknown_tool_rejection(self):
        res = self.registry.execute("malicious_unregistered_command", {"arg": "value"})
        self.assertFalse(res["success"])
        self.assertIn("not in the authorized tool registry", res["error"])

    def test_type_error_handling(self):
        # Passing wrong arguments type
        res = self.registry.execute("get_object_info", {"wrong_argument_name": 123})
        self.assertFalse(res["success"])
        self.assertIn("Invalid arguments", res["error"])


if __name__ == "__main__":
    unittest.main()

