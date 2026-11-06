"""
PyQt6-based native interactive Chat Panel for PyMOL AI Copilot.
Runs LLM planning in a background QThread to ensure PyMOL GUI remains 100% responsive.
"""

import html
import json
import logging
import os
import tempfile
import time
from typing import Any, Dict, List, Optional

try:
    from pymol import Qt
    QtWidgets = Qt.QtWidgets
    QtCore = Qt.QtCore
    QtGui = Qt.QtGui
except ImportError:
    from PyQt6 import QtWidgets, QtCore, QtGui

from ..agent.controller import AgentController
from ..agent.ollama_client import OllamaClient
from ..agent.tools import GLOBAL_CONTEXT
from ..config import CONFIG

logger = logging.getLogger(__name__)


_TOOL_SUMMARY_KEYS = (
    "selection", "target_selection", "object_name", "object", "atom_count",
    "count", "residue_count", "contact_count", "candidates_count",
    "target_count", "shown", "hidden", "color", "transparency", "oriented",
    "zoomed", "representation", "output_path", "file_path", "saved_to",
    "objects", "ligands", "message",
)


def summarize_tool_result(result: Any, max_chars: int = 320) -> str:
    """Build a short, human-readable summary without cutting JSON in half."""
    if not isinstance(result, dict):
        text = str(result)
    elif not result.get("success", True):
        text = f"error: {result.get('error', 'unknown error')}"
    else:
        parts = []
        for key in _TOOL_SUMMARY_KEYS:
            if key not in result:
                continue
            value = result[key]
            if value in (None, "", [], {}):
                continue
            if isinstance(value, list):
                value = f"[{len(value)} items]"
            elif isinstance(value, dict):
                value = f"{{{len(value)} fields}}"
            parts.append(f"{key}={value}")
        text = ", ".join(parts) if parts else "ok"

    if len(text) > max_chars:
        return text[:max_chars].rstrip() + "…"
    return text


def _atomic_write_json(path: str, data: Dict[str, Any]) -> None:
    """Write JSON atomically so a crash cannot leave a truncated history."""
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".ai_copilot_", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


class AgentWorker(QtCore.QThread):
    """Background worker thread running the agentic loop without blocking PyMOL."""
    step_signal = QtCore.pyqtSignal(dict)
    finished_signal = QtCore.pyqtSignal(dict)
    error_signal = QtCore.pyqtSignal(str)

    def __init__(self, controller: AgentController, instruction: str, max_steps: int, temperature: float):
        super().__init__()
        self.controller = controller
        self.instruction = instruction
        self.max_steps = max_steps
        self.temperature = temperature

    def run(self):
        try:
            result = self.controller.run(
                user_instruction=self.instruction,
                max_steps=self.max_steps,
                temperature=self.temperature,
                step_callback=self._on_step
            )
            self.finished_signal.emit(result)
        except Exception as e:
            logger.exception("Agent worker failed")
            self.error_signal.emit(str(e))

    def _on_step(self, event: Dict[str, Any]):
        self.step_signal.emit(event)

    def cancel(self):
        self.controller.cancel()


class ChatInputField(QtWidgets.QTextEdit):
    """TextEdit that submits on Enter and inserts newline on Shift+Enter."""
    submit_requested = QtCore.pyqtSignal()

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if event.key() in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
            if event.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.submit_requested.emit()
        else:
            super().keyPressEvent(event)


class CopilotDialog(QtWidgets.QDialog):
    """
    Main PyMOL AI Copilot interactive dialog.
    Non-modal, persistent, thread-safe, and single-instance.
    """
    _instance: Optional["CopilotDialog"] = None

    @classmethod
    def get_instance(cls, parent=None) -> "CopilotDialog":
        if cls._instance is None:
            cls._instance = cls(parent)
        return cls._instance

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PyMOL AI Copilot")
        self.resize(780, 820)
        self.setModal(False)

        # Initialize backend components
        self.ollama_client = OllamaClient(CONFIG.ollama_host, CONFIG.request_timeout_seconds)
        self.controller = AgentController(self.ollama_client, model_name=CONFIG.default_model)
        self.worker: Optional[AgentWorker] = None
        self._raw_chat_log: List[Dict[str, Any]] = []
        self._model_capabilities: Dict[str, Dict[str, Any]] = {}

        self._build_ui()
        self._restore_conversation()
        self.refresh_ollama_models()
        self.refresh_structure_context()

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # Top Control Bar: Connection, Model Selection, Temp, Max Steps
        top_group = QtWidgets.QGroupBox("AI Engine & Model Configuration")
        top_layout = QtWidgets.QHBoxLayout(top_group)
        top_layout.setContentsMargins(8, 8, 8, 8)

        # Status badge
        self.status_indicator = QtWidgets.QLabel("●")
        self.status_indicator.setStyleSheet("color: #7f8c8d; font-size: 16px; font-weight: bold;")
        self.status_label = QtWidgets.QLabel("Checking...")
        self.status_label.setStyleSheet("font-weight: bold;")
        top_layout.addWidget(self.status_indicator)
        top_layout.addWidget(self.status_label)

        top_layout.addSpacing(10)

        # Model selector
        top_layout.addWidget(QtWidgets.QLabel("Model:"))
        self.model_combo = QtWidgets.QComboBox()
        self.model_combo.setMinimumWidth(180)
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        top_layout.addWidget(self.model_combo)

        # Refresh models button
        self.btn_refresh_models = QtWidgets.QPushButton("⟳")
        self.btn_refresh_models.setToolTip("Refresh local Ollama models")
        self.btn_refresh_models.setMaximumWidth(32)
        self.btn_refresh_models.clicked.connect(self.refresh_ollama_models)
        top_layout.addWidget(self.btn_refresh_models)

        top_layout.addSpacing(10)

        # Temperature
        top_layout.addWidget(QtWidgets.QLabel("Temp:"))
        self.temp_spin = QtWidgets.QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 1.0)
        self.temp_spin.setSingleStep(0.05)
        self.temp_spin.setValue(CONFIG.temperature)
        self.temp_spin.setToolTip("Lower temperature (0.0-0.2) gives more deterministic tool calls.")
        self.temp_spin.valueChanged.connect(lambda _value: self._persist_settings())
        top_layout.addWidget(self.temp_spin)

        # Max steps
        top_layout.addWidget(QtWidgets.QLabel("Max Steps:"))
        self.steps_spin = QtWidgets.QSpinBox()
        self.steps_spin.setRange(1, 25)
        self.steps_spin.setValue(CONFIG.max_agent_steps)
        self.steps_spin.setToolTip("Maximum tool execution iterations per user request.")
        self.steps_spin.valueChanged.connect(lambda _value: self._persist_settings())
        top_layout.addWidget(self.steps_spin)

        top_layout.addStretch()
        main_layout.addWidget(top_group)

        # Middle Area: Splitter between Structure Context and Chat
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)

        # Structure Context Summary Panel
        context_group = QtWidgets.QGroupBox("PyMOL Structure Context")
        context_layout = QtWidgets.QHBoxLayout(context_group)
        context_layout.setContentsMargins(8, 6, 8, 6)

        self.context_label = QtWidgets.QLabel("No objects detected.")
        self.context_label.setWordWrap(True)
        self.context_label.setStyleSheet("color: #2c3e50; font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace; font-size: 11px;")
        context_layout.addWidget(self.context_label, 1)

        self.btn_refresh_context = QtWidgets.QPushButton("Refresh State")
        self.btn_refresh_context.setMaximumWidth(110)
        self.btn_refresh_context.clicked.connect(self.refresh_structure_context)
        context_layout.addWidget(self.btn_refresh_context)

        splitter.addWidget(context_group)

        # Chat Conversation Display
        chat_container = QtWidgets.QWidget()
        chat_layout = QtWidgets.QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(0, 0, 0, 0)

        self.chat_history = QtWidgets.QTextBrowser()
        self.chat_history.setOpenExternalLinks(False)
        self.chat_history.setStyleSheet("""
            QTextBrowser {
                background-color: #fafbfc;
                border: 1px solid #d0d7de;
                border-radius: 6px;
                padding: 10px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                font-size: 13px;
                line-height: 1.5;
            }
        """)
        chat_layout.addWidget(self.chat_history)
        splitter.addWidget(chat_container)

        splitter.setSizes([75, 450])
        main_layout.addWidget(splitter, 1)

        # Quick Presets Bar
        presets_layout = QtWidgets.QHBoxLayout()
        presets_layout.addWidget(QtWidgets.QLabel("<b>Quick Presets:</b>"))

        btn_cartoon = QtWidgets.QPushButton("Cartoon (Chains)")
        btn_cartoon.clicked.connect(lambda: self.quick_prompt("Show current protein as cartoon, color chains differently, and set background white."))
        presets_layout.addWidget(btn_cartoon)

        btn_pocket = QtWidgets.QPushButton("Binding Pocket")
        btn_pocket.clicked.connect(lambda: self.quick_prompt("Identify residues within 5 angstroms of the ligand and highlight the binding pocket."))
        presets_layout.addWidget(btn_pocket)

        btn_align = QtWidgets.QPushButton("Align & RMSD")
        btn_align.clicked.connect(lambda: self.quick_prompt("Align the loaded proteins, calculate their RMSD, and report structural differences."))
        presets_layout.addWidget(btn_align)

        btn_mut = QtWidgets.QPushButton("Analyze Mutation")
        btn_mut.clicked.connect(lambda: self.quick_prompt("Analyze residue 132 in chain A and identify neighboring residues within 5 angstroms."))
        presets_layout.addWidget(btn_mut)

        presets_layout.addStretch()
        main_layout.addLayout(presets_layout)

        # Input Area: Message box, Send, Cancel, Clear
        input_layout = QtWidgets.QHBoxLayout()

        self.input_text = ChatInputField()
        self.input_text.setPlaceholderText("Ask PyMOL AI Copilot (e.g. 'Show cartoon with chain colors', 'Measure distances < 4Å between ligand and protein')...")
        self.input_text.setMaximumHeight(70)
        self.input_text.submit_requested.connect(self.send_message)
        input_layout.addWidget(self.input_text, 1)

        btn_col = QtWidgets.QVBoxLayout()
        self.btn_send = QtWidgets.QPushButton("Send")
        self.btn_send.setStyleSheet("background-color: #0969da; color: white; font-weight: bold; padding: 6px 16px; border-radius: 4px;")
        self.btn_send.clicked.connect(self.send_message)
        btn_col.addWidget(self.btn_send)

        self.btn_stop = QtWidgets.QPushButton("Stop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("background-color: #cf222e; color: white; padding: 4px 12px; border-radius: 4px;")
        self.btn_stop.clicked.connect(self.cancel_agent)
        btn_col.addWidget(self.btn_stop)

        input_layout.addLayout(btn_col)
        main_layout.addLayout(input_layout)

        # Bottom Actions Bar: Export Script, Save Session, Render PNG, Clear
        bottom_layout = QtWidgets.QHBoxLayout()

        self.btn_export_pml = QtWidgets.QPushButton("Export Script (.pml)")
        self.btn_export_pml.setToolTip("Export all executed actions as a PyMOL macro script")
        self.btn_export_pml.clicked.connect(self.export_script)
        bottom_layout.addWidget(self.btn_export_pml)

        self.btn_save_pse = QtWidgets.QPushButton("Save Session (.pse)")
        self.btn_save_pse.setToolTip("Save the current PyMOL workspace session")
        self.btn_save_pse.clicked.connect(self.save_session)
        bottom_layout.addWidget(self.btn_save_pse)

        self.btn_render_png = QtWidgets.QPushButton("Render Image (.png)")
        self.btn_render_png.setToolTip("Export publication-quality ray-traced PNG")
        self.btn_render_png.clicked.connect(self.render_image)
        bottom_layout.addWidget(self.btn_render_png)

        self.btn_export_log = QtWidgets.QPushButton("Save Chat Log")
        self.btn_export_log.clicked.connect(self.export_chat_log)
        bottom_layout.addWidget(self.btn_export_log)

        bottom_layout.addStretch()

        self.btn_clear = QtWidgets.QPushButton("Clear Chat")
        self.btn_clear.clicked.connect(self.clear_chat)
        bottom_layout.addWidget(self.btn_clear)

        main_layout.addLayout(bottom_layout)

        # Append initial welcome message
        self._append_system_message(
            "<b>PyMOL AI Copilot ready.</b> Type a natural-language structural biology instruction or click a preset to start."
        )

    # --- Model and Connection Management ---

    def refresh_ollama_models(self):
        """Fetch available models from local Ollama service."""
        try:
            connected, msg = self.ollama_client.check_connection()
            if not connected:
                self.status_indicator.setStyleSheet("color: #e74c3c; font-size: 16px; font-weight: bold;")
                self.status_label.setText("Ollama Offline")
                self.status_label.setToolTip(
                    f"Could not reach Ollama at {CONFIG.ollama_host}: {msg}\n"
                    "Start it with `ollama serve` (or open the Ollama app)."
                )
                self.model_combo.clear()
                self.btn_send.setEnabled(False)
                self.btn_send.setToolTip(
                    "Ollama is offline. Start it with `ollama serve`, then click ⟳."
                )
                return

            self.status_indicator.setStyleSheet("color: #2ecc71; font-size: 16px; font-weight: bold;")
            self.status_label.setText("Ollama Online")
            self.status_label.setToolTip("Connected to Ollama")

            models = self.ollama_client.list_models()
            self.model_combo.blockSignals(True)
            current_sel = self.model_combo.currentText()
            self.model_combo.clear()
            self._model_capabilities.clear()

            default_idx = 0
            for idx, m in enumerate(models):
                self._model_capabilities[m["name"]] = m
                label = f"{m['name']} ({m['parameter_size']}, {m['size_gb']}GB)"
                self.model_combo.addItem(label, m["name"])
                if m["name"] == CONFIG.default_model or m["name"] in current_sel:
                    default_idx = idx

            if models:
                self.model_combo.setCurrentIndex(default_idx)
                selected_model = self.model_combo.itemData(default_idx)
                self.controller.model_name = selected_model
                self._update_model_warning(selected_model)
            else:
                self.btn_send.setEnabled(False)
                self.btn_send.setToolTip(
                    "No Ollama models installed. Run `ollama pull qwen2.5-coder:7b`."
                )
                self.status_label.setToolTip(
                    "No models installed. Run `ollama pull qwen2.5-coder:7b`."
                )

            self.model_combo.blockSignals(False)
            if models and not (self.worker and self.worker.isRunning()):
                self.btn_send.setEnabled(True)
                self.btn_send.setToolTip("")

        except Exception as e:
            self.status_indicator.setStyleSheet("color: #e74c3c; font-size: 16px; font-weight: bold;")
            self.status_label.setText("Connection Error")
            self.status_label.setToolTip(str(e))
            self.btn_send.setEnabled(False)

    def _update_model_warning(self, model_name: str):
        """Warn when the selected model does not advertise tool support."""
        info = self._model_capabilities.get(model_name) or {}
        capabilities = info.get("capabilities") or []
        if capabilities and "tools" not in capabilities:
            self.status_indicator.setStyleSheet("color: #d29922; font-size: 16px; font-weight: bold;")
            self.status_label.setText("No Tool Support")
            self.status_label.setToolTip(
                f"Model '{model_name}' does not advertise tool calling. "
                "The agent may narrate instead of executing. Prefer "
                "qwen2.5-coder:7b or another tool-capable model."
            )
        else:
            self.status_indicator.setStyleSheet("color: #2ecc71; font-size: 16px; font-weight: bold;")
            self.status_label.setText("Ollama Online")
            self.status_label.setToolTip(f"Active model: {model_name}")

    def _on_model_changed(self, text: str):
        model_name = self.model_combo.currentData()
        if model_name:
            self.controller.model_name = model_name
            CONFIG.default_model = model_name
            self._persist_settings()
            self._update_model_warning(model_name)

    def _persist_settings(self):
        """Persist the model/temperature/step settings chosen in the UI."""
        try:
            CONFIG.temperature = float(self.temp_spin.value())
            CONFIG.max_agent_steps = int(self.steps_spin.value())
            CONFIG.save()
        except Exception:
            logger.warning("Could not persist Copilot settings", exc_info=True)

    def _restore_conversation(self):
        """Restore the last conversation after a PyMOL restart."""
        if not CONFIG.persist_conversation:
            return
        path = CONFIG.get_conversation_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            logger.warning("Could not read persisted Copilot conversation", exc_info=True)
            return

        raw_messages = data.get("messages") if isinstance(data, dict) else None
        if not isinstance(raw_messages, list):
            return
        messages = [
            {"role": entry["role"], "content": entry["content"]}
            for entry in raw_messages
            if isinstance(entry, dict)
            and entry.get("role") in ("user", "assistant")
            and isinstance(entry.get("content"), str)
            and entry["content"].strip()
        ]
        if not messages:
            return

        limit = int(CONFIG.max_history_messages)
        if limit > 0:
            messages = messages[-limit:]
        while messages and messages[0]["role"] != "user":
            messages.pop(0)
        if not messages:
            return

        self.controller.conversation_history = messages
        focus = data.get("focus") if isinstance(data, dict) else None
        if isinstance(focus, dict):
            self.controller._last_focus = focus

        self._append_system_message(
            f"<i>Restored {len(messages)} message(s) from the previous session. "
            "Use <b>Clear Chat</b> to start fresh.</i>"
        )
        for entry in messages:
            if entry["role"] == "user":
                self._append_user_message(entry["content"])
            else:
                self._append_assistant_message(entry["content"])

    def _persist_conversation(self):
        """Save the bounded user/assistant history and follow-up focus."""
        if not CONFIG.persist_conversation:
            return
        messages = list(self.controller.conversation_history)
        limit = int(CONFIG.max_history_messages)
        if limit > 0:
            messages = messages[-limit:]
        while messages and messages[0].get("role") != "user":
            messages.pop(0)
        payload = {
            "version": 1,
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "messages": messages,
            "focus": getattr(self.controller, "_last_focus", None),
        }
        try:
            _atomic_write_json(CONFIG.get_conversation_path(), payload)
        except Exception:
            logger.warning("Could not persist Copilot conversation", exc_info=True)

    @staticmethod
    def _remove_conversation_file():
        path = CONFIG.get_conversation_path()
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            logger.warning("Could not remove persisted Copilot conversation", exc_info=True)

    def closeEvent(self, event):
        """Flush settings and conversation when the panel is closed."""
        self._persist_settings()
        self._persist_conversation()
        super().closeEvent(event)

    def refresh_structure_context(self):
        """Update the structure context badge with loaded PyMOL objects."""
        try:
            summary = GLOBAL_CONTEXT.inspector.get_structure_summary()
            if summary["object_count"] == 0:
                self.context_label.setText("<b>0 objects loaded.</b> Load a PDB (e.g. <code>fetch 1ake</code>) to begin.")
            else:
                lines = []
                for obj in summary["objects"]:
                    chains = ", ".join(obj["chains"]) if obj["chains"] else "none"
                    ligs = f", Ligands: {len(obj['ligands'])}" if obj["ligands"] else ""
                    lines.append(f"<b>{obj['name']}</b> ({obj['total_atoms']} atoms, Chains: [{chains}]{ligs})")
                self.context_label.setText(" | ".join(lines))
        except Exception as e:
            self.context_label.setText(f"Error inspecting PyMOL session: {e}")

    # --- Chat and Agent Execution ---

    def quick_prompt(self, text: str):
        self.input_text.setText(text)
        self.send_message()

    def send_message(self):
        text = self.input_text.toPlainText().strip()
        if not text:
            return

        if self.worker and self.worker.isRunning():
            QtWidgets.QMessageBox.warning(self, "Agent Busy", "An instruction is already being processed. Please wait or click Stop.")
            return

        self.input_text.clear()
        self._append_user_message(text)

        # Disable/enable UI buttons
        self.btn_send.setEnabled(False)
        self.btn_stop.setEnabled(True)

        max_steps = self.steps_spin.value()
        temp = self.temp_spin.value()

        # Launch worker
        self.worker = AgentWorker(self.controller, text, max_steps, temp)
        self.worker.step_signal.connect(self._on_worker_step)
        self.worker.finished_signal.connect(self._on_worker_finished)
        self.worker.error_signal.connect(self._on_worker_error)
        self.worker.start()

    def cancel_agent(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self._append_system_message("<i>Cancellation requested... waiting for thread to exit safely.</i>")
            self.btn_stop.setEnabled(False)

    def _on_worker_step(self, event: Dict[str, Any]):
        event_type = event.get("type")
        if event_type == "thinking_start":
            step = event.get("step")
            max_s = event.get("max_steps")
            self._append_status_line(f"🤖 <i>Step {step}/{max_s}: Agent planning actions...</i>")
        elif event_type == "tool_start":
            tool_name = event.get("tool")
            args = event.get("arguments", {})
            args_str = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
            self._append_tool_call(tool_name, args_str)
            self._raw_chat_log.append({
                "role": "tool",
                "time": time.strftime("%H:%M:%S"),
                "tool": tool_name,
                "phase": "call",
                "content": args_str,
            })
        elif event_type == "tool_result":
            tool_name = event.get("tool")
            res = event.get("result", {})
            self._append_tool_result(tool_name, res)
            self._raw_chat_log.append({
                "role": "tool",
                "time": time.strftime("%H:%M:%S"),
                "tool": tool_name,
                "phase": "result",
                "content": summarize_tool_result(res, max_chars=1000),
            })
            self.refresh_structure_context()
        elif event_type == "tool_retry":
            tool_name = event.get("tool")
            attempt = event.get("attempt")
            self._append_status_line(
                f"<span style='color:#9a6700;'>↻ Retrying {html.escape(str(tool_name))} "
                f"(attempt {attempt}) after a transient error.</span>"
            )
        elif event_type == "execution_nudge":
            self._append_status_line("⚙️ <i>Running the matched workflow instead of only describing it...</i>")
        elif event_type == "failure_nudge":
            self._append_status_line("↻ <i>Retrying with corrected arguments after a tool failure...</i>")
        elif event_type == "truthfulness_nudge":
            self._append_status_line("🔎 <i>No tool data yet — requiring verification before reporting results...</i>")
        elif event_type == "error":
            self._append_system_message(f"<b style='color:#cf222e;'>Error:</b> {event.get('error')}")

    def _on_worker_finished(self, result: Dict[str, Any]):
        self.btn_send.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.refresh_structure_context()

        final_resp = result.get("final_response", "")
        if final_resp:
            self._append_assistant_message(final_resp)

        dur = result.get("total_duration_seconds", 0)
        steps = result.get("steps_count", 0)
        self._append_status_line(f"<span style='color: #656d76; font-size: 11px;'>Completed in {dur}s ({steps} steps) using {result.get('model_used')}</span>")
        self._persist_conversation()

    def _on_worker_error(self, error_str: str):
        self.btn_send.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._append_system_message(f"<b style='color:#cf222e;'>Execution Error:</b> {html.escape(error_str)}")

    # --- HTML Message Rendering Helpers ---

    def _append_user_message(self, text: str):
        escaped = html.escape(text).replace("\n", "<br>")
        html_block = f"""
        <div style="margin: 10px 0; text-align: right;">
            <div style="display: inline-block; background-color: #ddf4ff; color: #0969da; border: 1px solid #54aeff; border-radius: 8px; padding: 8px 12px; text-align: left; max-width: 85%;">
                <b>User:</b><br>{escaped}
            </div>
        </div>
        """
        self.chat_history.append(html_block)
        self._raw_chat_log.append({"role": "user", "time": time.strftime("%H:%M:%S"), "content": text})

    def _append_assistant_message(self, text: str):
        escaped = html.escape(text).replace("\n", "<br>")
        html_block = f"""
        <div style="margin: 10px 0; text-align: left;">
            <div style="display: inline-block; background-color: #f6f8fa; color: #1f2328; border: 1px solid #d0d7de; border-radius: 8px; padding: 8px 12px; max-width: 90%;">
                <b style="color: #1a7f37;">AI Copilot:</b><br>{escaped}
            </div>
        </div>
        """
        self.chat_history.append(html_block)
        self._raw_chat_log.append({"role": "assistant", "time": time.strftime("%H:%M:%S"), "content": text})

    def _append_tool_call(self, tool_name: str, args_str: str):
        html_block = f"""
        <div style="margin: 4px 0 2px 16px; font-size: 12px; color: #57606a;">
            ⚙️ <b>Execute tool:</b> <code style="background-color: #eaeef2; padding: 2px 4px; border-radius: 3px;">{html.escape(tool_name)}({html.escape(args_str)})</code>
        </div>
        """
        self.chat_history.append(html_block)

    def _append_tool_result(self, tool_name: str, result: Dict[str, Any]):
        success = result.get("success", True)
        icon = "✓" if success else "✗"
        color = "#1a7f37" if success else "#cf222e"
        summary = summarize_tool_result(result)

        html_block = f"""
        <div style="margin: 2px 0 8px 24px; font-size: 11px; font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace; color: {color};">
            {icon} <b>{html.escape(tool_name)} result:</b> {html.escape(summary)}
        </div>
        """
        self.chat_history.append(html_block)

    def _append_system_message(self, msg: str):
        html_block = f"<div style='margin: 6px 0; color: #57606a; font-size: 12px;'>{msg}</div>"
        self.chat_history.append(html_block)

    def _append_status_line(self, line: str):
        html_block = f"<div style='margin: 4px 0; font-size: 11px; color: #656d76;'>{line}</div>"
        self.chat_history.append(html_block)

    def clear_chat(self):
        self.chat_history.clear()
        self.controller.clear_conversation()
        self._remove_conversation_file()
        self._raw_chat_log.clear()
        self._append_system_message("<i>Conversation history cleared.</i>")

    # --- Export and Actions ---

    def export_script(self):
        """Export executed commands as .pml script."""
        default_path = os.path.join(CONFIG.export_dir, "copilot_session.pml")
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export PyMOL Script", default_path, "PyMOL Script (*.pml)")
        if file_path:
            res = GLOBAL_CONTEXT.executor.get_pml_script()
            try:
                os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(res)
                QtWidgets.QMessageBox.information(self, "Export Successful", f"Saved PyMOL script to:\n{file_path}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Export Error", f"Failed to save script: {e}")

    def save_session(self):
        """Save PyMOL session file (.pse)."""
        default_path = os.path.join(CONFIG.export_dir, "session.pse")
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save PyMOL Session", default_path, "PyMOL Session (*.pse)")
        if file_path:
            try:
                saved = GLOBAL_CONTEXT.executor.save_session(file_path)
                QtWidgets.QMessageBox.information(self, "Session Saved", f"PyMOL session saved to:\n{saved}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Save Error", f"Failed to save session: {e}")

    def render_image(self):
        """Render high-resolution PNG image."""
        default_path = os.path.join(CONFIG.export_dir, "render.png")
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Render Image", default_path, "PNG Image (*.png)")
        if file_path:
            try:
                saved = GLOBAL_CONTEXT.executor.export_image(file_path, CONFIG.default_image_width, CONFIG.default_image_height, CONFIG.default_image_dpi, ray=1)
                QtWidgets.QMessageBox.information(self, "Image Rendered", f"High-resolution ray-traced image saved to:\n{saved}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Render Error", f"Failed to render image: {e}")

    def export_chat_log(self):
        """Save full chat log."""
        default_path = os.path.join(CONFIG.export_dir, "copilot_chat_log.json")
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Chat Log", default_path, "JSON Log (*.json);;Text Log (*.txt)")
        if file_path:
            try:
                os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
                if file_path.endswith(".json"):
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(self._raw_chat_log, f, indent=2)
                else:
                    with open(file_path, "w", encoding="utf-8") as f:
                        for entry in self._raw_chat_log:
                            f.write(f"[{entry.get('time', '')}] {entry.get('role', '').upper()}:\n{entry.get('content', '')}\n\n")
                QtWidgets.QMessageBox.information(self, "Log Saved", f"Chat log saved to:\n{file_path}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Export Error", f"Failed to save log: {e}")

