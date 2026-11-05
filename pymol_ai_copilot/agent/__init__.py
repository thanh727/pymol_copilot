"""
Agent module for autonomous LLM planning, Ollama interaction, and tool orchestration.
"""

from .controller import AgentController
from .ollama_client import OllamaClient
from .prompts import SYSTEM_PROMPT, format_context_prompt
from .tool_registry import GLOBAL_REGISTRY, ToolDefinition, ToolRegistry

__all__ = [
    "AgentController",
    "OllamaClient",
    "SYSTEM_PROMPT",
    "format_context_prompt",
    "GLOBAL_REGISTRY",
    "ToolDefinition",
    "ToolRegistry"
]

