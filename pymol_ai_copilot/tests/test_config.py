"""
Unit tests for configuration management.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import patch
from pymol_ai_copilot.config import CopilotConfig


class TestConfig(unittest.TestCase):
    def test_default_values(self):
        cfg = CopilotConfig()
        self.assertEqual(cfg.ollama_host, "http://127.0.0.1:11434")
        self.assertEqual(cfg.max_agent_steps, 8)
        self.assertAlmostEqual(cfg.temperature, 0.1)
        self.assertTrue(cfg.default_ray_trace)
        self.assertEqual(cfg.default_image_dpi, 300)
        self.assertTrue(cfg.persist_conversation)

    def test_get_conversation_path(self):
        path = CopilotConfig.get_conversation_path()
        self.assertTrue(path.endswith("ai_copilot_conversation.json"))
        self.assertTrue(os.path.isabs(path))

    def test_custom_config(self):
        cfg = CopilotConfig(
            ollama_host="http://localhost:11434",
            max_agent_steps=12,
            temperature=0.2
        )
        self.assertEqual(cfg.max_agent_steps, 12)
        self.assertAlmostEqual(cfg.temperature, 0.2)

    def test_get_config_path(self):
        path = CopilotConfig.get_config_path()
        self.assertTrue(path.endswith("ai_copilot_config.json"))
        self.assertTrue(os.path.isabs(path))

    def test_save_is_atomic_and_loadable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "ai_copilot_config.json")
            cfg = CopilotConfig(max_agent_steps=11)
            cfg.additional_export_dirs = [os.path.join(tmpdir, "extra")]

            with patch.object(CopilotConfig, "get_config_path", return_value=path):
                cfg.save()
                loaded = CopilotConfig.load()

            self.assertTrue(os.path.exists(path))
            self.assertEqual(loaded.max_agent_steps, 11)
            self.assertEqual(loaded.additional_export_dirs, [os.path.join(tmpdir, "extra")])

            with open(path, encoding="utf-8") as f:
                json.load(f)  # must remain valid JSON

            leftovers = [n for n in os.listdir(tmpdir) if n.startswith(".ai_copilot_config.")]
            self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()

