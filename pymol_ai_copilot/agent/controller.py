"""
Autonomous Agent Controller implementing the Observe -> Plan -> Execute -> Inspect -> Continue/Finish loop.
"""

import json
import time
from typing import Any, Callable, Dict, List, Optional

from ..config import CONFIG
from .ollama_client import OllamaClient, OllamaClientError
from .prompts import format_context_prompt
from .tool_registry import GLOBAL_REGISTRY, ToolRegistry
from .tools import GLOBAL_CONTEXT
from .workflow_engine import GLOBAL_WORKFLOW_REGISTRY, WorkflowDefinition, WorkflowSession, WorkflowState


class AgentStep:
    """Represents a single step in the agent's reasoning and execution loop."""
    def __init__(self, step_number: int):
        self.step_number = step_number
        self.thinking: str = ""
        self.tool_calls: List[Dict[str, Any]] = []
        self.tool_results: List[Dict[str, Any]] = []
        self.content: str = ""
        self.duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step_number,
            "thinking": self.thinking,
            "tool_calls": self.tool_calls,
            "tool_results": self.tool_results,
            "content": self.content,
            "duration_ms": self.duration_ms
        }


class AgentController:
    """
    Orchestrates the multi-step agent loop, coordinating LLM planning and PyMOL tool execution.
    """

    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        registry: Optional[ToolRegistry] = None,
        model_name: Optional[str] = None
    ):
        self.client = ollama_client or OllamaClient(CONFIG.ollama_host, CONFIG.request_timeout_seconds)
        self.registry = registry or GLOBAL_REGISTRY
        self.model_name = model_name or CONFIG.default_model
        self.conversation_history: List[Dict[str, Any]] = []
        self._cancelled = False

    def cancel(self):
        """Cancel current agent execution."""
        self._cancelled = True
        self.client.cancel()

    def reset_cancellation(self):
        self._cancelled = False
        self.client.reset_cancellation()

    def clear_conversation(self):
        """Clear conversation history."""
        self.conversation_history.clear()

    def run(
        self,
        user_instruction: str,
        max_steps: Optional[int] = None,
        temperature: Optional[float] = None,
        step_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Execute the agent loop for a user instruction.

        Args:
            user_instruction: Natural language prompt from user.
            max_steps: Maximum autonomous tool steps (default from CONFIG).
            temperature: LLM temperature (default from CONFIG).
            step_callback: Optional callback receiving step progress dictionaries.

        Returns:
            Dictionary containing final_response, steps, tool_executions, and success status.
        """
        if self._cancelled:
            return {
                "success": True,
                "cancelled": True,
                "final_response": "Execution was cancelled by the user.",
                "steps_count": 0,
                "steps": [],
                "total_duration_seconds": 0.0,
                "model_used": self.model_name
            }
        steps_limit = max_steps or CONFIG.max_agent_steps
        temp = temperature if temperature is not None else CONFIG.temperature

        # 1. Observe: Inspect current PyMOL context
        current_context = GLOBAL_CONTEXT.inspector.get_context_for_prompt()
        system_prompt = format_context_prompt(current_context)

        # 2. Scientific Workflow Matching & Entity Resolution
        try:
            loaded_objs = GLOBAL_CONTEXT.inspector.get_loaded_objects()
        except Exception:
            loaded_objs = []
        matched_wf, entities, confidence = GLOBAL_WORKFLOW_REGISTRY.match_workflow(user_instruction, loaded_objs)
        wf_session: Optional[WorkflowSession] = None

        if matched_wf:
            wf_session = WorkflowSession(matched_wf, entities, intent_match_confidence=confidence)
            wf_session.start()
            # Context-dependent tool scoping: expose only approved relevant capabilities
            tools_schema = self.registry.get_ollama_tools(subset=matched_wf.required_capabilities)
            # Inject declarative workflow execution guidance
            wf_prompt = matched_wf.generate_guidance_prompt(entities)
            system_prompt = f"{system_prompt}\n\n{wf_prompt}"
            if step_callback:
                step_callback({
                    "type": "workflow_selected",
                    "workflow_id": matched_wf.workflow_id,
                    "name": matched_wf.name,
                    "confidence": confidence,
                    "entities": entities
                })
        else:
            tools_schema = self.registry.get_ollama_tools()

        # Prepare messages
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt}
        ]

        # Append previous conversation history for context continuity
        messages.extend(self.conversation_history)

        # Append current user prompt
        messages.append({"role": "user", "content": user_instruction})

        # Also store user instruction in persistent history
        self.conversation_history.append({"role": "user", "content": user_instruction})

        executed_steps: List[AgentStep] = []
        final_answer = ""
        total_start_time = time.time()

        # Track failed tool signatures to prevent infinite retry loops
        failed_signatures: set = set()
        consecutive_repeated_failures = 0
        early_stopped_due_to_loop = False

        for step_idx in range(1, steps_limit + 1):
            if self._cancelled or early_stopped_due_to_loop:
                if self._cancelled:
                    final_answer = "Execution was cancelled by the user."
                break

            step = AgentStep(step_idx)
            step_start = time.time()

            if step_callback:
                step_callback({
                    "type": "thinking_start",
                    "step": step_idx,
                    "max_steps": steps_limit
                })

            try:
                # Query LLM
                response = self.client.chat(
                    model=self.model_name,
                    messages=messages,
                    tools=tools_schema,
                    temperature=temp
                )
            except OllamaClientError as e:
                error_msg = f"LLM communication error: {e}"
                final_answer = f"Error during agent planning: {error_msg}"
                if step_callback:
                    step_callback({"type": "error", "error": error_msg})
                break

            step.thinking = response.get("thinking", "")
            step.content = response.get("content", "")
            tool_calls = response.get("tool_calls", [])
            step.duration_ms = round((time.time() - step_start) * 1000, 2)

            # If no tool calls were made, the agent decided it is done or explaining directly
            if not tool_calls:
                final_answer = step.content
                executed_steps.append(step)

                # Record assistant response in conversation history
                self.conversation_history.append({"role": "assistant", "content": final_answer})

                if step_callback:
                    step_callback({
                        "type": "final_response",
                        "step": step_idx,
                        "content": final_answer
                    })
                break

            # Execute the tool calls sequentially
            step.tool_calls = tool_calls

            # Append the assistant's action to messages
            messages.append({
                "role": "assistant",
                "content": step.content,
                "tool_calls": [
                    {
                        "id": tc.get("id", f"call_{tc['name']}"),
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc["arguments"]
                        }
                    }
                    for tc in tool_calls
                ]
            })

            step_has_repeated = False
            for tc in tool_calls:
                if self._cancelled:
                    break

                t_name = tc["name"]
                t_args = tc.get("arguments", {})
                if not isinstance(t_args, dict):
                    t_args = {}
                t_id = tc.get("id", f"call_{t_name}")

                # Serialize tool call signature for failure tracking
                try:
                    args_sig = json.dumps(t_args, sort_keys=True)
                except Exception:
                    args_sig = str(t_args)
                call_sig = f"{t_name}::{args_sig}"

                if step_callback:
                    step_callback({
                        "type": "tool_start",
                        "step": step_idx,
                        "tool": t_name,
                        "arguments": t_args
                    })

                # Check if this exact call signature previously failed
                if call_sig in failed_signatures:
                    # Detect and block repeating an identical failed tool call
                    step_has_repeated = True
                    consecutive_repeated_failures += 1
                    tool_res = {
                        "success": False,
                        "error": (
                            f"Execution rejected: Tool call '{t_name}' with arguments {args_sig} "
                            f"already failed in a previous step. Repeating identical failed calls is disallowed. "
                            f"Choose an alternative valid strategy from the authorized tools or report the limitation."
                        ),
                        "repeated_failure": True
                    }
                else:
                    # Validate tool presence in authorized registry
                    tool_def = self.registry.get(t_name)
                    if tool_def is None:
                        # Non-existent or unauthorized tool call
                        auth_tools = [t.name for t in self.registry.list_tools()]
                        tool_res = {
                            "success": False,
                            "error": (
                                f"Tool '{t_name}' is not in the authorized tool registry. "
                                f"This is a non-retryable error. Do not call '{t_name}' again. "
                                f"Available authorized tools: {auth_tools}"
                            ),
                            "non_retryable": True
                        }
                        failed_signatures.add(call_sig)
                    else:
                        # Execute tool via registry
                        tool_res = self.registry.execute(t_name, t_args)
                        if not tool_res.get("success", False):
                            failed_signatures.add(call_sig)
                        else:
                            consecutive_repeated_failures = 0  # Reset on successful execution

                step.tool_results.append({
                    "tool": t_name,
                    "arguments": t_args,
                    "result": tool_res
                })

                if wf_session:
                    wf_session.record_tool_call(t_name, t_args, tool_res, step.duration_ms)

                if step_callback:
                    step_callback({
                        "type": "tool_result",
                        "step": step_idx,
                        "tool": t_name,
                        "result": tool_res
                    })

                # Feed result back into conversation
                messages.append({
                    "role": "tool",
                    "tool_call_id": t_id,
                    "name": t_name,
                    "content": json.dumps(tool_res)
                })

            executed_steps.append(step)

            # Check if agent is trapped in an unrecoverable failure loop
            if step_has_repeated or consecutive_repeated_failures >= 2:
                early_stopped_due_to_loop = True
                break

        # If max steps reached without final answer, do one final synthesis call
        if not final_answer and not self._cancelled:
            if early_stopped_due_to_loop:
                synthesis_prompt = (
                    "Execution stopped early because an invalid or failed tool call was repeated without a valid alternative strategy. "
                    "Please provide a helpful, concise response explaining what was attempted, what was invalid, "
                    "and guide the user on how to accomplish the task using authorized tools (e.g. fetch_structure or load_structure)."
                )
            else:
                synthesis_prompt = (
                    "You have completed your tool execution steps. Please provide a clear, concise scientific summary "
                    "of the actions performed, structural findings, and visual updates now visible in PyMOL."
                )
            messages.append({"role": "user", "content": synthesis_prompt})
            try:
                synth_resp = self.client.chat(
                    model=self.model_name,
                    messages=messages,
                    tools=None,
                    temperature=temp
                )
                final_answer = synth_resp.get("content", "Task execution finished.")
            except Exception as e:
                final_answer = f"Task completed {len(executed_steps)} tool execution step(s). (Synthesis summary error: {e})"

            self.conversation_history.append({"role": "assistant", "content": final_answer})
            if step_callback:
                step_callback({
                    "type": "final_response",
                    "step": len(executed_steps),
                    "content": final_answer
                })

        total_time = round(time.time() - total_start_time, 2)

        exec_record = None
        if wf_session:
            exec_record = wf_session.finalize(cancelled=self._cancelled)

        # Scientific provenance and verification audit
        provenance = {
            "workflow_id": matched_wf.workflow_id if matched_wf else "ad-hoc",
            "workflow_name": matched_wf.name if matched_wf else "Unstructured",
            "confidence": confidence if matched_wf else 0.0,
            "entities": entities if matched_wf else {},
            "pymol_version": "3.1.0",
            "units": {"distances": "angstroms", "angles": "degrees", "rmsd": "angstroms"},
            "tools_executed": [tr["tool"] for s in executed_steps for tr in s.tool_results if tr["result"].get("success")],
            "scientific_limitations": matched_wf.scientific_limitations if matched_wf else []
        }

        # Success determination: do not claim success if execution stopped early due to unrecovered failure
        is_success = not self._cancelled
        all_results = [tr["result"] for s in executed_steps for tr in s.tool_results]
        if all_results and all(not r.get("success", False) for r in all_results):
            is_success = False

        if exec_record and exec_record.state == WorkflowState.FAILED:
            is_success = False

        return {
            "success": is_success,
            "status": "success" if is_success else ("cancelled" if self._cancelled else "failed"),
            "cancelled": self._cancelled,
            "final_response": final_answer,
            "steps_count": len(executed_steps),
            "steps": [s.to_dict() for s in executed_steps],
            "total_duration_seconds": total_time,
            "model_used": self.model_name,
            "workflow": matched_wf.workflow_id if matched_wf else None,
            "workflow_execution": exec_record.to_dict() if exec_record else None,
            "workflow_state": exec_record.state.value if exec_record else None,
            "scientific_measurements": exec_record.scientific_measurements if exec_record else {},
            "provenance": provenance
        }
