"""
Unit tests for configuration management.
"""

import os
import unittest
from pymol_ai_copilot.config import CONFIG, CopilotConfig


class TestConfig(unittest.TestCase):
    def test_default_values(self):
        cfg = CopilotConfig()
        self.assertEqual(cfg.ollama_host, "http://127.0.0.1:11434")
        self.assertEqual(cfg.max_agent_steps, 8)
        self.assertAlmostEqual(cfg.temperature, 0.1)
        self.assertTrue(cfg.default_ray_trace)
        self.assertEqual(cfg.default_image_dpi, 300)

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


if __name__ == "__main__":
    unittest.main()

