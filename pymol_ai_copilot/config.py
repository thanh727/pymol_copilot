"""
Configuration and settings management for PyMOL AI Copilot.
"""

import json
import logging
import os
import tempfile
from dataclasses import asdict, dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CopilotConfig:
    ollama_host: str = "http://127.0.0.1:11434"
    default_model: str = "qwen2.5-coder:7b"
    temperature: float = 0.1
    max_agent_steps: int = 8
    request_timeout_seconds: int = 60
    max_history_messages: int = 20
    max_tool_result_chars: int = 8000
    default_image_width: int = 1920
    default_image_height: int = 1080
    default_image_dpi: int = 300
    default_ray_trace: bool = True
    export_dir: str = field(default_factory=lambda: os.path.expanduser("~/pymol_ai_exports"))
    # Extra directories the agent may write exports to. The system temporary
    # directory and ``export_dir`` are always allowed.
    additional_export_dirs: list = field(default_factory=list)
    # Restore the last user/assistant exchange when PyMOL starts again.
    persist_conversation: bool = True

    @classmethod
    def get_config_path(cls) -> str:
        pymol_dir = os.path.expanduser("~/.pymol")
        os.makedirs(pymol_dir, exist_ok=True)
        return os.path.join(pymol_dir, "ai_copilot_config.json")

    @classmethod
    def get_conversation_path(cls) -> str:
        pymol_dir = os.path.expanduser("~/.pymol")
        os.makedirs(pymol_dir, exist_ok=True)
        return os.path.join(pymol_dir, "ai_copilot_conversation.json")

    @classmethod
    def load(cls) -> "CopilotConfig":
        path = cls.get_config_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            except Exception:
                logger.warning("Failed to load config from %s; using defaults.", path, exc_info=True)
        return cls()

    def save(self) -> None:
        """Persist the configuration atomically.

        Writing to a temporary file in the same directory and replacing the
        target prevents a crash or full disk from leaving a truncated, invalid
        JSON file behind.
        """
        path = self.get_config_path()
        tmp_path = None
        try:
            directory = os.path.dirname(path) or "."
            os.makedirs(directory, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(prefix=".ai_copilot_config.", suffix=".tmp", dir=directory)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
            tmp_path = None
        except Exception as e:
            print(f"[PyMOL AI Copilot] Warning: failed to save config to {path}: {e}")
        finally:
            if tmp_path:
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass


# Global config instance
CONFIG = CopilotConfig.load()

