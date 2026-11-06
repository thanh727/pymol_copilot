"""
PyMOL AI Copilot - Native Agentic AI Plugin for Open-Source PyMOL.

Public attributes are imported lazily so that lightweight consumers (for example
the installer or headless analysis scripts) do not require PyQt/PyMOL at import
time.
"""

from importlib import import_module
from typing import Any

__version__ = "1.0.0"

__all__ = [
    "__init_plugin__",
    "show_copilot_window",
    "AgentController",
    "OllamaClient",
    "CONFIG",
    "CopilotConfig",
]

_LAZY_ATTRS = {
    "__init_plugin__": (".plugin", "__init_plugin__"),
    "show_copilot_window": (".plugin", "show_copilot_window"),
    "AgentController": (".agent.controller", "AgentController"),
    "OllamaClient": (".agent.ollama_client", "OllamaClient"),
    "CONFIG": (".config", "CONFIG"),
    "CopilotConfig": (".config", "CopilotConfig"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_ATTRS:
        module_name, attr_name = _LAZY_ATTRS[name]
        # Relative import keeps the plugin working when PyMOL autoloads it as
        # ``pmg_tk.startup.pymol_ai_copilot`` instead of ``pymol_ai_copilot``.
        value = getattr(import_module(module_name, __name__), attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
