"""
Ollama HTTP API client supporting dynamic model discovery and tool calling.
Uses Python's standard library (urllib) for maximum reliability and zero external dependencies.
"""

import json
import re
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Tuple


class OllamaClientError(Exception):
    """Base exception for Ollama client errors."""
    pass


class OllamaConnectionError(OllamaClientError):
    """Raised when Ollama server cannot be reached."""
    pass


class OllamaTimeoutError(OllamaClientError):
    """Raised when Ollama server times out."""
    pass


class OllamaClient:
    """
    Communicates with local Ollama service.
    """

    def __init__(self, host: str = "http://127.0.0.1:11434", timeout: int = 60):
        self.host = host.rstrip("/")
        self.timeout = timeout
        self._cancelled = False

    def cancel(self):
        """Signal cancellation for long-running operations."""
        self._cancelled = True

    def reset_cancellation(self):
        self._cancelled = False

    def check_connection(self) -> Tuple[bool, str]:
        """Check if Ollama server is responding."""
        url = f"{self.host}/api/tags"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "PyMOL-AI-Copilot/1.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    return True, "Connected to Ollama"
                return False, f"HTTP status {resp.status}"
        except urllib.error.URLError as e:
            return False, f"Connection failed: {e.reason}"
        except Exception as e:
            return False, str(e)

    def list_models(self) -> List[Dict[str, Any]]:
        """
        Query GET /api/tags to list locally installed models.
        """
        url = f"{self.host}/api/tags"
        req = urllib.request.Request(url, headers={"User-Agent": "PyMOL-AI-Copilot/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = data.get("models", [])
                result = []
                for m in models:
                    details = m.get("details", {})
                    caps = m.get("capabilities", [])
                    result.append({
                        "name": m.get("name"),
                        "model": m.get("model"),
                        "size_gb": round(m.get("size", 0) / (1024**3), 2),
                        "parameter_size": details.get("parameter_size", "unknown"),
                        "quantization": details.get("quantization_level", "unknown"),
                        "family": details.get("family", "unknown"),
                        "supports_tools": "tools" in caps
                    })
                return result
        except urllib.error.URLError as e:
            raise OllamaConnectionError(f"Cannot connect to Ollama at {self.host}: {e.reason}") from e
        except TimeoutError as e:
            raise OllamaTimeoutError(f"Ollama request timed out after {self.timeout}s.") from e
        except Exception as e:
            raise OllamaClientError(f"Error fetching Ollama models: {e}") from e

    def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.1,
        stream_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Send a chat completion request to Ollama POST /api/chat.
        Supports native tools and returns parsed message with tool calls.
        """
        self.reset_cancellation()
        url = f"{self.host}/api/chat"

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": float(temperature)
            }
        }

        if tools:
            payload["tools"] = tools

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "PyMOL-AI-Copilot/1.0"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if self._cancelled:
                    raise OllamaClientError("Request was cancelled by user.")

                raw_bytes = resp.read()
                response_json = json.loads(raw_bytes.decode("utf-8"))
                message = response_json.get("message", {})

                # Parse tool calls from message
                tool_calls = self._extract_tool_calls(message)

                return {
                    "role": message.get("role", "assistant"),
                    "content": message.get("content", ""),
                    "thinking": message.get("thinking", ""),
                    "tool_calls": tool_calls,
                    "total_duration_ms": round(response_json.get("total_duration", 0) / 1e6, 2)
                }

        except urllib.error.URLError as e:
            if self._cancelled:
                raise OllamaClientError("Request cancelled.") from e
            raise OllamaConnectionError(f"Failed to communicate with Ollama: {e.reason}") from e
        except TimeoutError as e:
            raise OllamaTimeoutError(f"Chat request timed out after {self.timeout} seconds.") from e
        except Exception as e:
            if self._cancelled:
                raise OllamaClientError("Request cancelled.") from e
            raise OllamaClientError(f"Chat request failed: {e}") from e

    def _extract_tool_calls(self, message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract tool calls from response message.
        Handles:
        1. Native Ollama/OpenAI 'tool_calls' array: [{'function': {'name': '...', 'arguments': {...}}}]
        2. Markdown JSON code blocks in 'content': ```json { ... } ```
        3. Multi-line JSON Lines in 'content': '{"name": "..."}\n{"name": "..."}'
        4. Single JSON object or array in 'content'
        """
        extracted = []

        # 1. Check native tool_calls field
        native_calls = message.get("tool_calls")
        if native_calls and isinstance(native_calls, list):
            for call in native_calls:
                func = call.get("function", {})
                name = func.get("name")
                args = func.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {}
                if name:
                    extracted.append({
                        "id": call.get("id", f"call_{name}"),
                        "name": name,
                        "arguments": args
                    })

        if extracted:
            return extracted

        # 2. Check content
        content = message.get("content", "").strip()
        if not content:
            return []

        # 2a. Check for markdown code blocks
        json_blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        for block in json_blocks:
            try:
                parsed = json.loads(block)
                if isinstance(parsed, dict) and "name" in parsed:
                    extracted.append({
                        "id": f"call_{parsed['name']}",
                        "name": parsed["name"],
                        "arguments": parsed.get("arguments", {})
                    })
            except Exception:
                pass

        if extracted:
            return extracted

        # 2b. Check for JSON lines (common when LLMs emit multiple tool calls)
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    parsed = json.loads(line)
                    if isinstance(parsed, dict) and "name" in parsed:
                        extracted.append({
                            "id": f"call_{parsed['name']}",
                            "name": parsed["name"],
                            "arguments": parsed.get("arguments", {})
                        })
                except Exception:
                    pass

        if extracted:
            return extracted

        # 2c. Check for whole JSON object or array
        if content.startswith("{") and content.endswith("}"):
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict) and "name" in parsed:
                    extracted.append({
                        "id": f"call_{parsed['name']}",
                        "name": parsed["name"],
                        "arguments": parsed.get("arguments", {})
                    })
            except Exception:
                pass
        elif content.startswith("[") and content.endswith("]"):
            try:
                parsed = json.loads(content)
                if isinstance(parsed, list):
                    for item in parsed:
                        if isinstance(item, dict) and "name" in item:
                            extracted.append({
                                "id": f"call_{item['name']}",
                                "name": item["name"],
                                "arguments": item.get("arguments", {})
                            })
            except Exception:
                pass

        return extracted
