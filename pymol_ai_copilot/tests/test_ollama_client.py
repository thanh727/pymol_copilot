"""
Unit tests for Ollama client and tool calling extraction.
"""

import json
import unittest
from pymol_ai_copilot.agent.ollama_client import OllamaClient


class TestOllamaClient(unittest.TestCase):
    def setUp(self):
        self.client = OllamaClient()

    def test_extract_native_tool_calls(self):
        msg = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_123",
                    "function": {
                        "name": "list_objects",
                        "arguments": {"object_type": "all"}
                    }
                }
            ]
        }
        extracted = self.client._extract_tool_calls(msg)
        self.assertEqual(len(extracted), 1)
        self.assertEqual(extracted[0]["name"], "list_objects")
        self.assertEqual(extracted[0]["arguments"], {"object_type": "all"})

    def test_extract_content_json_tool_calls(self):
        # Format commonly emitted by Qwen2.5-coder
        msg = {
            "role": "assistant",
            "content": '{"name": "show_representation", "arguments": {"representation": "cartoon", "selection": "all"}}'
        }
        extracted = self.client._extract_tool_calls(msg)
        self.assertEqual(len(extracted), 1)
        self.assertEqual(extracted[0]["name"], "show_representation")
        self.assertEqual(extracted[0]["arguments"]["representation"], "cartoon")

    def test_extract_markdown_json_blocks(self):
        msg = {
            "role": "assistant",
            "content": "Let me execute that:\n```json\n{\n  \"name\": \"color_selection\",\n  \"arguments\": {\"color\": \"bychain\"}\n}\n```"
        }
        extracted = self.client._extract_tool_calls(msg)
        self.assertEqual(len(extracted), 1)
        self.assertEqual(extracted[0]["name"], "color_selection")
        self.assertEqual(extracted[0]["arguments"]["color"], "bychain")

    def test_plain_text_no_tool_calls(self):
        msg = {
            "role": "assistant",
            "content": "I have aligned the two proteins. The calculated RMSD is 1.42 Å over 214 aligned atoms."
        }
        extracted = self.client._extract_tool_calls(msg)
        self.assertEqual(len(extracted), 0)

    def test_live_ollama_connection(self):
        # Check actual local Ollama service
        connected, msg = self.client.check_connection()
        if connected:
            models = self.client.list_models()
            self.assertIsInstance(models, list)
            self.assertGreaterEqual(len(models), 1)


if __name__ == "__main__":
    unittest.main()

