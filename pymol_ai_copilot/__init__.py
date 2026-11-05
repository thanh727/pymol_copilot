"""
PyMOL AI Copilot - Native Agentic AI Plugin for Open-Source PyMOL.
"""

from .plugin import __init_plugin__, show_copilot_window
from .agent.controller import AgentController
from .agent.ollama_client import OllamaClient
from .config import CONFIG, CopilotConfig

__version__ = "1.0.0"
__all__ = [
    "__init_plugin__",
    "show_copilot_window",
    "AgentController",
    "OllamaClient",
    "CONFIG",
    "CopilotConfig"
]

