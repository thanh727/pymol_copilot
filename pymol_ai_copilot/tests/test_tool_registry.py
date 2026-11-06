"""
Unit tests for ToolRegistry and Ollama schema generation.
"""

import os
import tempfile
import unittest
from pymol_ai_copilot.agent.tool_registry import GLOBAL_REGISTRY, ToolDefinition, ToolRegistry
from pymol_ai_copilot.agent.capability_registry import GLOBAL_CAPABILITY_REGISTRY


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

    def test_capability_registry_matches_tool_registry(self):
        """Capability metadata must not drift from the executable tool schemas."""
        tool_names = {t.name for t in self.registry.list_tools()}
        cap_names = {c.name for c in GLOBAL_CAPABILITY_REGISTRY.list_authorized_tools()}
        self.assertEqual(tool_names, cap_names)

        for name in sorted(tool_names):
            tool = self.registry.get(name)
            cap = GLOBAL_CAPABILITY_REGISTRY.get(name)
            self.assertIsNotNone(cap, f"Capability for '{name}' is missing.")
            self.assertEqual(cap.parameters, tool.parameters, f"Schema drift for '{name}'.")
            self.assertEqual(cap.description, tool.description, f"Description drift for '{name}'.")

    def test_label_residues_rejects_expression_injection(self):
        """Label expressions are evaluated by PyMOL, so arbitrary strings must be rejected."""
        payload = 'x" or __import__("os").system("echo pwned") or "'
        res = self.registry.execute("label_residues", {
            "selection": "all",
            "label_type": payload
        })
        self.assertFalse(res["success"])
        self.assertIn("Unsupported label_type", res["error"])

    def test_type_error_handling(self):
        # Passing wrong arguments type
        res = self.registry.execute("get_object_info", {"wrong_argument_name": 123})
        self.assertFalse(res["success"])
        self.assertIn("Invalid arguments", res["error"])

    def test_internal_type_error_is_not_reported_as_invalid_arguments(self):
        def broken_tool(value):
            raise TypeError("bug inside the tool implementation")

        registry = ToolRegistry()
        registry.register(ToolDefinition(
            name="internal_type_error_probe",
            description="Test tool that raises TypeError internally.",
            parameters={"type": "object", "properties": {"value": {"type": "string"}}},
            func=broken_tool
        ))

        res = registry.execute("internal_type_error_probe", {"value": "ok"})

        self.assertFalse(res["success"])
        self.assertIn("internal TypeError", res["error"])
        self.assertNotIn("Invalid arguments", res["error"])

    def test_export_outside_allowed_roots_is_rejected(self):
        forbidden = os.path.expanduser("~/copilot_forbidden_export_test.json")
        res = self.registry.execute("export_analysis_json", {
            "filename": forbidden,
            "data": {"should": "not be written"}
        })

        self.assertFalse(res["success"])
        self.assertIn("Refusing to write outside the allowed export directories", res["error"])
        self.assertFalse(os.path.exists(forbidden))

    def test_export_rejects_symlink_escape(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            link = os.path.join(tmpdir, "escape")
            try:
                os.symlink("/private/etc", link)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks are not available on this platform.")

            target = os.path.join(link, "copilot_escape_test.json")
            res = self.registry.execute("export_analysis_json", {
                "filename": target,
                "data": {"should": "not be written"}
            })

            self.assertFalse(res["success"])
            self.assertIn("Refusing to write outside", res["error"])
            self.assertFalse(os.path.exists("/private/etc/copilot_escape_test.json"))

    def test_export_inside_temp_directory_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = os.path.join(tmpdir, "analysis.json")
            res = self.registry.execute("export_analysis_json", {
                "filename": target,
                "data": {"workflow": "test"}
            })

            self.assertTrue(res["success"], res.get("error"))
            self.assertTrue(os.path.exists(target))


if __name__ == "__main__":
    unittest.main()

