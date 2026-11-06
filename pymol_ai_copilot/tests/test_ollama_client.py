"""
Unit tests for Ollama client and tool calling extraction.
"""

import json
import unittest
from unittest.mock import patch
from pymol_ai_copilot.agent.ollama_client import OllamaClient, OllamaClientError


class _FakeStreamResponse:
    """Minimal context-manager/iterable emulating an HTTP streaming response."""

    def __init__(self, chunks):
        self._chunks = [json.dumps(c).encode("utf-8") + b"\n" for c in chunks]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def __iter__(self):
        return iter(self._chunks)


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

    def test_streamed_content_is_aggregated(self):
        chunks = [
            {"message": {"role": "assistant", "content": "Hello "}},
            {"message": {"role": "assistant", "content": "world"}, "done": False},
            {"message": {"role": "assistant", "content": "!"}, "done": True,
             "total_duration": 5_000_000},
        ]

        with patch(
            "pymol_ai_copilot.agent.ollama_client.urllib.request.urlopen",
            return_value=_FakeStreamResponse(chunks)
        ) as mock_open:
            result = self.client.chat("test-model", [{"role": "user", "content": "hi"}])

        self.assertEqual(result["content"], "Hello world!")
        self.assertEqual(result["total_duration_ms"], 5.0)
        payload = json.loads(mock_open.call_args[0][0].data.decode("utf-8"))
        self.assertTrue(payload["stream"])

    def test_streamed_tool_calls_are_aggregated(self):
        chunks = [
            {"message": {"role": "assistant", "content": ""}},
            {"message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "call_1",
                    "function": {"name": "list_objects", "arguments": {"object_type": "all"}}
                }]
            }, "done": True},
        ]

        with patch(
            "pymol_ai_copilot.agent.ollama_client.urllib.request.urlopen",
            return_value=_FakeStreamResponse(chunks)
        ):
            result = self.client.chat("test-model", [{"role": "user", "content": "list"}])

        self.assertEqual(len(result["tool_calls"]), 1)
        self.assertEqual(result["tool_calls"][0]["name"], "list_objects")
        self.assertEqual(result["tool_calls"][0]["arguments"], {"object_type": "all"})

    def test_streaming_stops_when_cancelled(self):
        chunks = [
            {"message": {"role": "assistant", "content": "first"}},
            {"message": {"role": "assistant", "content": "second"}, "done": True},
        ]

        def cancel_after_first(chunk):
            self.client.cancel()

        with patch(
            "pymol_ai_copilot.agent.ollama_client.urllib.request.urlopen",
            return_value=_FakeStreamResponse(chunks)
        ):
            with self.assertRaises(OllamaClientError):
                self.client.chat(
                    "test-model",
                    [{"role": "user", "content": "hi"}],
                    stream_callback=cancel_after_first
                )


if __name__ == "__main__":
    unittest.main()

