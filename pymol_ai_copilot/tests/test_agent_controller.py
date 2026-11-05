"""
Unit tests for the autonomous AgentController loop.
"""

import unittest
from unittest.mock import MagicMock
from pymol_ai_copilot.agent.controller import AgentController
from pymol_ai_copilot.agent.tool_registry import GLOBAL_REGISTRY


class TestAgentController(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.controller = AgentController(
            ollama_client=self.mock_client,
            registry=GLOBAL_REGISTRY,
            model_name="mock-model"
        )

    def test_single_turn_text_response(self):
        # LLM returns text directly without tool calls
        self.mock_client.chat.return_value = {
            "role": "assistant",
            "content": "PDB 1AKE is adenylate kinase with an open conformation.",
            "tool_calls": []
        }

        result = self.controller.run("Tell me about 1AKE", max_steps=3)
        self.assertTrue(result["success"])
        self.assertEqual(result["steps_count"], 1)
        self.assertIn("adenylate kinase", result["final_response"])

    def test_multi_step_tool_loop(self):
        # Step 1: Model calls list_objects
        # Step 2: Model returns final response
        self.mock_client.chat.side_effect = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "name": "list_objects",
                        "arguments": {}
                    }
                ]
            },
            {
                "role": "assistant",
                "content": "I have listed the objects and found none currently loaded.",
                "tool_calls": []
            }
        ]

        events = []
        def callback(evt):
            events.append(evt["type"])

        result = self.controller.run("Check loaded objects", max_steps=4, step_callback=callback)
        self.assertTrue(result["success"])
        self.assertEqual(result["steps_count"], 2)
        self.assertIn("tool_start", events)
        self.assertIn("tool_result", events)
        self.assertIn("final_response", events)
        self.assertIn("listed the objects", result["final_response"])

    def test_cancellation(self):
        self.controller.cancel()
        result = self.controller.run("Test instruction", max_steps=3)
        self.assertTrue(result["cancelled"])
        self.assertIn("cancelled", result["final_response"])


if __name__ == "__main__":
    unittest.main()

