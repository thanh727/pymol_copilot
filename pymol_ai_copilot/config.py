"""
Configuration and settings management for PyMOL AI Copilot.
"""

import json
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


@dataclass
class CopilotConfig:
    ollama_host: str = "http://127.0.0.1:11434"
    default_model: str = "qwen2.5-coder:7b"
    temperature: float = 0.1
    max_agent_steps: int = 8
    request_timeout_seconds: int = 60
    default_image_width: int = 1920
    default_image_height: int = 1080
    default_image_dpi: int = 300
    default_ray_trace: bool = True
    export_dir: str = field(default_factory=lambda: os.path.expanduser("~/pymol_ai_exports"))

    @classmethod
    def get_config_path(cls) -> str:
        pymol_dir = os.path.expanduser("~/.pymol")
        os.makedirs(pymol_dir, exist_ok=True)
        return os.path.join(pymol_dir, "ai_copilot_config.json")

    @classmethod
    def load(cls) -> "CopilotConfig":
        path = cls.get_config_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            except Exception:
                pass
        return cls()

    def save(self) -> None:
        path = self.get_config_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=2)
        except Exception as e:
            print(f"[PyMOL AI Copilot] Warning: failed to save config to {path}: {e}")


# Global config instance
CONFIG = CopilotConfig.load()

