"""
Autonomous Agent Controller implementing the Observe -> Plan -> Execute -> Inspect -> Continue/Finish loop.
"""

import json
import re
import time
from typing import Any, Callable, Dict, List, Optional

from ..config import CONFIG
from ..pymol_bridge.version import get_pymol_version
from .capability_registry import ErrorClassification, classify_error
from .ollama_client import (
    OllamaClient,
    OllamaClientError,
    OllamaConnectionError,
    OllamaTimeoutError,
)
from .prompts import format_context_prompt
from .tool_registry import GLOBAL_REGISTRY, ToolRegistry
from .tools import GLOBAL_CONTEXT
from .workflow_engine import GLOBAL_WORKFLOW_REGISTRY, EntityExtractor, WorkflowSession, WorkflowState


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

    # Transient tool failures (network timeouts, dropped connections) are retried
    # with exponential backoff instead of poisoning the failed-call cache forever.
    TRANSIENT_RETRIES = 2
    TRANSIENT_BACKOFF_SECONDS = 0.25

    # Read-only introspection may legitimately be repeated after the session
    # changes. Every other identical successful call is treated as a loop.
    _REPEATABLE_READ_TOOLS = {
        "list_objects", "get_object_info", "get_structure_summary", "get_chains",
        "get_residues", "get_selection_info", "count_atoms", "identify_ligands",
    }

    _ACTION_PATTERN = re.compile(
        r"\b(?:fetch|download|load|find|identify|analy[sz]e|calculate|compute|show|"
        r"display|visuali[sz]e|render|colou?r|align|compare|measure|export|save|"
        r"select|highlight|label|list|inspect|determine|count|trace|orient|zoom)\b",
        re.IGNORECASE
    )
    _ACTION_TERMS_VI = (
        "tải", "tìm", "xác định", "tính", "hiển thị", "phân tích", "liệt kê",
        "vẽ", "chọn", "căn chỉnh", "so sánh", "đo ", "xuất", "lưu", "đánh dấu",
        "kiểm tra", "mô tả", "tương tác"
    )

    _CONTACT_TERMS = (
        "tương tác", "interaction", "contact", "binding pocket", "binding site",
        "túi gắn", "residue", "residues", "dư lượng"
    )

    _VI_DIACRITICS = re.compile(
        r"[àáảãạăằắẳẵặâầấẩẫậđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợ"
        r"ùúủũụưừứửữựỳýỷỹỵ]",
        re.IGNORECASE
    )

    @classmethod
    def _looks_actionable_instruction(cls, text: str) -> bool:
        """Heuristic: does this instruction ask for a concrete PyMOL action?"""
        lowered = text.lower()
        if cls._ACTION_PATTERN.search(lowered):
            return True
        return any(term in lowered for term in cls._ACTION_TERMS_VI)

    @classmethod
    def _looks_vietnamese(cls, text: str) -> bool:
        return bool(cls._VI_DIACRITICS.search(text))

    @classmethod
    def _is_contact_request(cls, text: str) -> bool:
        lowered = text.lower()
        return any(term in lowered for term in cls._CONTACT_TERMS)

    _CONTACT_TYPE_TERMS = (
        "loại tương tác", "kiểu tương tác", "loại liên kết", "bản chất tương tác",
        "interaction type", "type of interaction", "contact type", "types of interaction",
        "hydrogen bond", "liên kết hydro", "liên kết hydrogen", "polar contact",
        "hydrophobic contact", "salt bridge", "cầu muối"
    )

    @classmethod
    def _wants_contact_types(cls, text: str) -> bool:
        lowered = text.lower()
        return any(term in lowered for term in cls._CONTACT_TYPE_TERMS)

    _RESIDUE_LIST_TERMS = (
        "residue", "residues", "dư lượng", "amino acid", "axit amin",
        "liệt kê", "danh sách", "list "
    )
    _VISUAL_ONLY_TERMS = (
        "visualize", "visualise", "render", "display", "hiển thị", "vẽ"
    )

    @classmethod
    def _wants_residue_list(cls, text: str) -> bool:
        """Does the user explicitly want residue data rather than just a view?"""
        lowered = text.lower()
        if any(term in lowered for term in cls._VISUAL_ONLY_TERMS):
            has_type_request = any(term in lowered for term in cls._CONTACT_TYPE_TERMS)
            if not has_type_request:
                return False
        return any(term in lowered for term in cls._RESIDUE_LIST_TERMS)

    _PER_INSTANCE_TERMS = (
        "từng", "mỗi", "per-instance", "per instance", "per ligand",
        "per ion", "riêng lẻ", "riêng từng"
    )

    @classmethod
    def _wants_per_instance(cls, text: str) -> bool:
        lowered = text.lower()
        if any(term in lowered for term in cls._PER_INSTANCE_TERMS):
            return True
        return bool(re.search(r"\beach\b", lowered))

    # Pronouns and deictic phrases that point at the previous successful action.
    _ANAPHORA_PATTERN = re.compile(
        r"\b(?:it|its|them|they|that|those|this|these)\b"
        r"|\b(?:nó|chúng|cái đó|vùng đó|phần đó|chỗ đó|phân tử đó|ligand đó|"
        r"ion đó|residue đó|kết quả đó|tương tác đó|phức hợp đó)\b",
        re.IGNORECASE
    )

    # Selection-syntax tokens that make a prompt explicitly targeted even when
    # it also contains a pronoun.
    _EXPLICIT_SELECTION_PATTERN = re.compile(
        r"\b(?:resn|resi|chain|model|sele|polymer|byres|within|all)\b",
        re.IGNORECASE
    )

    @classmethod
    def _has_anaphora(cls, text: str) -> bool:
        return bool(cls._ANAPHORA_PATTERN.search(text))

    @classmethod
    def _is_pure_anaphoric_instruction(cls, text: str) -> bool:
        """True for short follow-ups such as "zoom in on it" with no target.

        Explicit entities/selections always win, so a prompt like
        "download 1UBQ and display it" is not treated as a dangling reference.
        """
        if not cls._has_anaphora(text):
            return False
        if cls._EXPLICIT_SELECTION_PATTERN.search(text):
            return False
        try:
            entities = EntityExtractor.extract_entities(text)
        except Exception:
            entities = {}
        if any(entities.get(key) for key in (
            "pdb_id", "alphafold_id", "ligand_resn", "mutation_str",
            "referenced_objects", "file_path"
        )):
            return False
        return len(text.split()) <= 14

    def _followup_focus_hint(self, user_instruction: str) -> str:
        """Resolve pronouns against the last successful tool target.

        The hint is injected into the system prompt so small local models do
        not have to infer a selection from raw conversation text.
        """
        if not self._has_anaphora(user_instruction):
            return ""

        focus = self._last_focus
        if not focus:
            if self._is_pure_anaphoric_instruction(user_instruction):
                return (
                    "\n\n## Follow-up Handling\n"
                    "The current message refers to a previous action, but no "
                    "successful action exists yet in this conversation. Ask the "
                    "user which object, ligand, or selection they mean instead "
                    "of guessing."
                )
            return ""

        selection = focus.get("selection") or ""
        object_name = focus.get("object") or ""
        resn = focus.get("resn") or ""
        resi = focus.get("resi") or ""
        chain = focus.get("chain") or ""

        target_bits = []
        if object_name:
            target_bits.append(f"object `{object_name}`")
        if selection:
            target_bits.append(f"selection `{selection}`")
        if resn:
            instance = f"{resn} {resi}".strip()
            if chain:
                instance += f" (chain {chain})"
            target_bits.append(f"ligand/ion `{instance}`")

        if not target_bits:
            return ""

        return (
            "\n\n## Follow-up Context\n"
            "The current message contains an implicit reference (for example "
            "\"it\", \"them\", \"that\", \"đó\", or \"nó\"). The last successful "
            f"action was `{focus.get('tool', 'unknown')}` on "
            + ", ".join(target_bits)
            + ". Resolve the reference against that target. Reuse its selection "
            "when the request needs one, do not ask the user to repeat it, and "
            "do not substitute a different object or ligand."
        )

    def _update_followup_focus(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Dict[str, Any]
    ) -> None:
        """Record the target of a successful tool call for follow-up turns."""
        if not result or not result.get("success", False):
            return

        focus: Dict[str, Any] = {"tool": tool_name}
        object_name = (
            result.get("object_name")
            or arguments.get("object_name")
            or arguments.get("object")
            or arguments.get("target")
            or arguments.get("object1")
            or arguments.get("wildtype_object")
        )
        if isinstance(object_name, str) and object_name.strip():
            focus["object"] = object_name.strip()

        selection = None
        for key in (
            "selection", "target_selection", "selection1", "highlighted",
            "labeled_selection", "zoomed", "oriented"
        ):
            value = result.get(key) or arguments.get(key)
            if isinstance(value, str) and value.strip():
                selection = value.strip()
                break
        if not selection:
            selection_name = result.get("name") or arguments.get("selection_name")
            selection_expr = result.get("selection") or arguments.get("selection_expr")
            if isinstance(selection_name, str) and selection_name.strip():
                selection = selection_name.strip()
            elif isinstance(selection_expr, str) and selection_expr.strip():
                selection = selection_expr.strip()
        if selection:
            focus["selection"] = selection

        resn = result.get("ligand_resn") or arguments.get("ligand_resn")
        resi = result.get("ligand_resi") or arguments.get("ligand_resi")
        chain = result.get("ligand_chain") or arguments.get("ligand_chain")
        if resn:
            focus["resn"] = str(resn)
            focus["resi"] = str(resi or "")
            focus["chain"] = str(chain or "")
        else:
            targets = result.get("targets") or []
            if targets and isinstance(targets[0], dict):
                first = targets[0]
                focus["resn"] = str(first.get("resn", ""))
                focus["resi"] = str(first.get("resi", ""))
                focus["chain"] = str(first.get("chain", ""))
                if len(targets) > 1 and focus.get("object"):
                    focus["selection"] = (
                        f"model {focus['object']} and resn '{focus['resn']}'"
                    )

        if len(focus) <= 1:
            return
        self._last_focus = focus

    def _resolve_ligand_target(self, user_instruction: str) -> Optional[Dict[str, Any]]:
        """Resolve the ligand/ion a contact request refers to.

        The lookup is grounded in the live session: a residue name must either be
        explicitly named in the instruction (e.g. ``SO4``) or be the only
        heteroatom present. This prevents the deterministic fallback from
        inventing a target for purely conceptual questions.
        """
        try:
            entities = EntityExtractor.extract_entities(user_instruction)
        except Exception:
            entities = {}

        try:
            summary = GLOBAL_CONTEXT.inspector.get_structure_summary()
        except Exception:
            return None

        objects = summary.get("objects", []) or []
        referenced = entities.get("referenced_objects") or []
        candidates: List[Dict[str, Any]] = []
        for obj in objects:
            obj_name = obj.get("name")
            if referenced and obj_name not in referenced:
                continue
            seen = set()
            hetero = list(obj.get("heteroatoms") or [])
            for lig in obj.get("ligands") or []:
                if lig not in hetero:
                    hetero.append(lig)
            for item in hetero:
                key = (item.get("resn"), item.get("resi"), item.get("chain"))
                if key in seen:
                    continue
                seen.add(key)
                candidates.append({
                    "object": obj_name,
                    "resn": str(item.get("resn", "")).upper(),
                    "resi": str(item.get("resi", "")),
                    "chain": str(item.get("chain", ""))
                })

        if not candidates:
            return None

        target: Optional[Dict[str, Any]] = None
        explicit = (entities.get("ligand_resn") or "").upper()
        if explicit:
            for candidate in candidates:
                if candidate["resn"] == explicit:
                    target = dict(candidate)
                    break
            if target is None and objects:
                # Allow a literal residue name the model/user supplied even when
                # the session summary missed it; the tool will validate it.
                target = {
                    "object": (referenced[0] if referenced else objects[0].get("name")),
                    "resn": explicit,
                    "resi": "",
                    "chain": ""
                }
        else:
            for candidate in candidates:
                if re.search(rf"\b{re.escape(candidate['resn'])}\b", user_instruction, re.IGNORECASE):
                    target = dict(candidate)
                    break

            if target is None:
                unique = {(c["object"], c["resn"]) for c in candidates}
                if len(unique) == 1:
                    target = dict(candidates[0])

        if target is None or not target.get("object"):
            return None

        try:
            target["cutoff"] = float(entities.get("cutoff") or 4.0)
        except (TypeError, ValueError):
            target["cutoff"] = 4.0
        return target

    def _run_fallback_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        step: "AgentStep",
        allowed_tool_names: Optional[set],
        step_callback: Optional[Callable[[Dict[str, Any]], None]],
        step_idx: int
    ) -> Optional[Dict[str, Any]]:
        """Execute a controller-initiated tool call and record it on ``step``."""
        if allowed_tool_names is not None and tool_name not in allowed_tool_names:
            return None
        try:
            if self.registry.get(tool_name) is None:
                return None
        except Exception:
            # Stub registries used in tests may not implement get()
            pass

        if step_callback:
            step_callback({
                "type": "tool_start",
                "step": step_idx,
                "tool": tool_name,
                "arguments": tool_args
            })

        result = self._execute_tool_with_retry(tool_name, tool_args, step_callback, step_idx)

        step.tool_calls.append({
            "id": f"fallback_{tool_name}",
            "name": tool_name,
            "arguments": tool_args
        })
        step.tool_results.append({
            "tool": tool_name,
            "arguments": tool_args,
            "result": result
        })

        if step_callback:
            step_callback({
                "type": "tool_result",
                "step": step_idx,
                "tool": tool_name,
                "result": result
            })

        if result and result.get("success", False):
            self._update_followup_focus(tool_name, tool_args, result)

        return result

    @staticmethod
    def _last_successful_result(
        executed_steps: List["AgentStep"],
        tool_name: str
    ) -> Optional[Dict[str, Any]]:
        result = None
        for executed in executed_steps:
            for tr in executed.tool_results:
                if tr["tool"] == tool_name and tr["result"].get("success", False):
                    result = tr["result"]
        return result

    @staticmethod
    def _answer_covers_instances(
        answer: str,
        proximity_result: Optional[Dict[str, Any]]
    ) -> bool:
        """Check whether the model's answer names every target instance."""
        if not proximity_result:
            return False
        items = proximity_result.get("per_instance") or []
        if len(items) <= 1:
            return True
        for item in items:
            target = item.get("target") or {}
            resi = str(target.get("resi", ""))
            if resi and re.search(rf"\b{re.escape(resi)}\b", answer):
                continue
            return False
        return True

    def _deterministic_contact_fallback(
        self,
        user_instruction: str,
        step: "AgentStep",
        allowed_tool_names: Optional[set],
        step_callback: Optional[Callable[[Dict[str, Any]], None]],
        step_idx: int
    ) -> Optional[str]:
        """Run a grounded contact analysis when the model refuses to call a tool.

        This is the last line of defense against plan-only answers: if the model
        will not execute, the controller resolves the ligand from the live
        session and calls the appropriate analysis tool itself.
        """
        target = self._resolve_ligand_target(user_instruction)
        if not target:
            return None

        resn = target["resn"]
        obj = target["object"]
        cutoff = target["cutoff"]
        model_sel = f"model {obj}"
        attempts = [
            (
                "analyze_ligand_interactions",
                {"object_name": obj, "ligand_resn": resn, "cutoff": cutoff}
            ),
            (
                "find_nearby_residues",
                {"target_selection": f"{model_sel} and resn '{resn}'", "cutoff": cutoff}
            )
        ]

        for tool_name, tool_args in attempts:
            result = self._run_fallback_tool(
                tool_name, tool_args, step, allowed_tool_names, step_callback, step_idx
            )
            if result and result.get("success", False):
                formatted = self._format_contact_fallback(
                    target, tool_name, result, user_instruction
                )
                if formatted:
                    return formatted

        return None

    def _deterministic_per_instance_fallback(
        self,
        user_instruction: str,
        step: "AgentStep",
        allowed_tool_names: Optional[set],
        executed_steps: List["AgentStep"],
        step_callback: Optional[Callable[[Dict[str, Any]], None]],
        step_idx: int
    ) -> Optional[str]:
        """Produce a per-ligand/ion contact breakdown without relying on the model."""
        target = self._resolve_ligand_target(user_instruction)
        if not target:
            return None

        proximity = self._last_successful_result(executed_steps, "find_nearby_residues")
        if not proximity or not proximity.get("per_instance"):
            selection = f"model {target['object']} and resn '{target['resn']}'"
            proximity = self._run_fallback_tool(
                "find_nearby_residues",
                {"target_selection": selection, "cutoff": target["cutoff"]},
                step,
                allowed_tool_names,
                step_callback,
                step_idx
            )
            if not proximity or not proximity.get("success", False):
                return None

        items = proximity.get("per_instance") or []
        if len(items) < 2:
            return None

        cutoff = proximity.get("cutoff_angstroms") or target["cutoff"]
        analyses: Dict[tuple, Dict[str, Any]] = {}
        if self._wants_contact_types(user_instruction):
            for item in items[:10]:
                instance = item.get("target") or {}
                args = {
                    "object_name": target["object"],
                    "ligand_resn": instance.get("resn", target["resn"]),
                    "ligand_resi": instance.get("resi", ""),
                    "ligand_chain": instance.get("chain", ""),
                    "cutoff": cutoff
                }
                result = self._run_fallback_tool(
                    "analyze_ligand_interactions",
                    args,
                    step,
                    allowed_tool_names,
                    step_callback,
                    step_idx
                )
                if result and result.get("success", False):
                    analyses[(instance.get("resn"), str(instance.get("resi", "")), instance.get("chain", ""))] = result

        return self._format_per_instance_fallback(
            target, proximity, analyses, user_instruction, cutoff
        )

    def _format_per_instance_fallback(
        self,
        target: Dict[str, Any],
        proximity: Dict[str, Any],
        analyses: Dict[tuple, Dict[str, Any]],
        user_instruction: str,
        cutoff: float
    ) -> Optional[str]:
        """Format one residue/contact section per ligand or ion instance."""
        vietnamese = self._looks_vietnamese(user_instruction)
        items = proximity.get("per_instance") or []
        if len(items) < 2:
            return None

        resn = target["resn"]
        obj = target["object"]
        if vietnamese:
            lines = [
                f"Kết quả theo từng phân tử **{resn}** trong `{obj}` "
                f"(cutoff {cutoff} Å): **{len(items)}** đối tượng."
            ]
        else:
            lines = [
                f"Per-instance results for **{resn}** in `{obj}` "
                f"(cutoff {cutoff} Å): **{len(items)}** instances."
            ]

        for item in items:
            instance = item.get("target") or {}
            residues = item.get("residues") or []
            instance_id = (
                f"{instance.get('resn', resn)} "
                f"{instance.get('resi', '')}:{instance.get('chain', '')}"
            ).strip()
            if vietnamese:
                lines.append(f"\n**{instance_id}** — {len(residues)} residue:")
            else:
                lines.append(f"\n**{instance_id}** — {len(residues)} residues:")

            key = (
                instance.get("resn"),
                str(instance.get("resi", "")),
                instance.get("chain", "")
            )
            analysis = analyses.get(key)
            contacts = (analysis or {}).get("contacts") or []
            if contacts:
                for contact in contacts:
                    residue_id = (
                        f"{contact.get('residue_name')}{contact.get('residue_number')}"
                    )
                    if contact.get("chain"):
                        residue_id += f" ({contact.get('chain')})"
                    contact_type = contact.get("contact_type", "unknown")
                    if contact_type != "polar":
                        contact_type = (
                            "kỵ nước/van der Waals" if vietnamese
                            else "hydrophobic/van der Waals"
                        )
                    if vietnamese:
                        lines.append(
                            f"  - **{residue_id}**: "
                            f"{contact.get('min_distance_angstrom')} Å — {contact_type}"
                        )
                    else:
                        lines.append(
                            f"  - **{residue_id}**: "
                            f"{contact.get('min_distance_angstrom')} Å — {contact_type}"
                        )
                continue

            if residues:
                ids = [
                    f"{r.get('resn')}{r.get('resi')}" + (
                        f" ({r.get('chain')})" if r.get("chain") else ""
                    )
                    for r in residues
                ]
                lines.append("  - " + ", ".join(ids))
            else:
                lines.append(
                    "  - Không có residue trong cutoff."
                    if vietnamese
                    else "  - No residues within the cutoff."
                )

        if vietnamese:
            lines.append(
                "\nLưu ý: mỗi nhóm được tính riêng theo từng phân tử/ion; "
                "đây là các tiếp xúc hình học, chưa phải bằng chứng năng lượng liên kết."
            )
        else:
            lines.append(
                "\nNote: each group is computed for its own ligand/ion instance; "
                "these are geometric contacts, not thermodynamic binding evidence."
            )
        return "\n".join(lines)

    _LABEL_TERMS = ("label", "nhãn", "ghi nhãn")
    _HIGHLIGHT_TERMS = (
        "highlight", "làm nổi bật", "nổi bật", "show as sticks", "show them as sticks",
        "hiển thị dạng sticks", "dạng sticks", "sticks"
    )

    @staticmethod
    def _contact_residue_selection(proximity: Dict[str, Any]) -> str:
        """Build a PyMOL selection from proximity or contact-analysis data."""
        residues = list(proximity.get("residues") or [])
        if not residues:
            for item in proximity.get("per_instance") or []:
                residues.extend(item.get("residues") or [])
        if not residues:
            for contact in proximity.get("contacts") or []:
                residue = {
                    "chain": contact.get("chain", ""),
                    "resi": contact.get("residue_number") or contact.get("resi", ""),
                    "resn": contact.get("residue_name", ""),
                }
                if residue["resi"]:
                    residues.append(residue)

        parts = []
        seen = set()
        for residue in residues[:200]:
            chain = str(residue.get("chain", ""))
            resi = str(residue.get("resi", ""))
            if not resi:
                continue
            key = (chain, resi)
            if key in seen:
                continue
            seen.add(key)
            if chain:
                parts.append(f"(chain '{chain}' and resi '{resi}')")
            else:
                parts.append(f"resi '{resi}'")
        return " or ".join(parts)

    def _last_contact_dataset(
        self,
        executed_steps: List["AgentStep"]
    ) -> Optional[Dict[str, Any]]:
        """Return the richest available residue-contact result from this run."""
        for tool_name in (
            "find_nearby_residues", "analyze_ligand_interactions",
            "inspect_binding_pocket"
        ):
            result = self._last_successful_result(executed_steps, tool_name)
            if result and self._contact_residue_selection(result):
                return result
        return None

    def _ensure_contact_visual_actions(
        self,
        user_instruction: str,
        step: "AgentStep",
        allowed_tool_names: Optional[set],
        executed_steps: List["AgentStep"],
        step_callback: Optional[Callable[[Dict[str, Any]], None]],
        step_idx: int
    ) -> Optional[str]:
        """Execute a requested label/highlight when the model only describes it."""
        if not self._is_contact_request(user_instruction):
            return None
        if not self._wants_residue_list(user_instruction):
            return None

        lowered = user_instruction.lower()
        wants_label = any(term in lowered for term in self._LABEL_TERMS)
        wants_highlight = any(term in lowered for term in self._HIGHLIGHT_TERMS)
        if not wants_label and not wants_highlight:
            return None

        contact_data = self._last_contact_dataset(executed_steps)
        if not contact_data:
            return None
        selection = self._contact_residue_selection(contact_data)
        if not selection:
            return None

        done_tools = {
            tr["tool"]
            for s in executed_steps for tr in s.tool_results
            if tr["result"].get("success", False)
        }
        residue_count = selection.count("resi '")
        notes = []

        if wants_label and "label_residues" not in done_tools:
            result = self._run_fallback_tool(
                "label_residues",
                {"selection": selection, "label_type": "resn_resi"},
                step,
                allowed_tool_names,
                step_callback,
                step_idx
            )
            if result and result.get("success", False):
                notes.append(
                    f"Labels added to {residue_count} contact residue(s)."
                )

        if wants_highlight and not (
            {"highlight_residues", "show_representation"} & done_tools
        ):
            result = self._run_fallback_tool(
                "highlight_residues",
                {"selection": selection, "representation": "sticks", "color": "yellow"},
                step,
                allowed_tool_names,
                step_callback,
                step_idx
            )
            if result and result.get("success", False):
                notes.append(
                    f"Contact residues highlighted as yellow sticks "
                    f"({result.get('highlighted', selection)})."
                )

        return " ".join(notes) if notes else None

    def _format_contact_fallback(
        self,
        target: Dict[str, Any],
        tool_name: str,
        result: Dict[str, Any],
        user_instruction: str
    ) -> Optional[str]:
        """Render a concise residue/contact-type summary in the user's language."""
        vietnamese = self._looks_vietnamese(user_instruction)
        resn = target["resn"]
        obj = target["object"]
        cutoff = target["cutoff"]

        if tool_name == "analyze_ligand_interactions":
            contacts = result.get("contacts") or []
            if not contacts:
                return None
            polar_count = sum(1 for c in contacts if c.get("contact_type") == "polar")
            hydrophobic_count = len(contacts) - polar_count

            if vietnamese:
                lines = [
                    f"Kết quả phân tích tương tác của **{resn}** trong `{obj}` "
                    f"(cutoff {cutoff} Å): **{len(contacts)} residue** tiếp xúc, "
                    f"{polar_count} residue có tiếp xúc polar, "
                    f"{hydrophobic_count} residue kỵ nước/van der Waals."
                ]
            else:
                lines = [
                    f"Interaction analysis for **{resn}** in `{obj}` "
                    f"(cutoff {cutoff} Å): **{len(contacts)} contacting residues**, "
                    f"{polar_count} with polar contacts, "
                    f"{hydrophobic_count} hydrophobic/van der Waals."
                ]

            for contact in contacts:
                res_name = contact.get("residue_name", "")
                res_num = contact.get("residue_number", "")
                chain = contact.get("chain", "")
                min_dist = contact.get("min_distance_angstrom")
                contact_type = contact.get("contact_type", "unknown")
                polar = contact.get("polar_contacts") or []

                if contact_type == "polar":
                    type_label = "polar" if vietnamese else "polar"
                else:
                    type_label = (
                        "kỵ nước/van der Waals" if vietnamese else "hydrophobic/van der Waals"
                    )

                residue_id = f"{res_name}{res_num}"
                if chain:
                    residue_id += f" ({chain})"

                if vietnamese:
                    detail = f"  - **{residue_id}**: {min_dist} Å — {type_label}"
                else:
                    detail = f"  - **{residue_id}**: {min_dist} Å — {type_label}"

                if polar:
                    pairs = "; ".join(
                        f"{p.get('residue_atom')}–{p.get('ligand_atom')} "
                        f"{p.get('distance_angstrom')} Å"
                        for p in polar[:3]
                    )
                    detail += (
                        f" (cặp nguyên tử: {pairs})" if vietnamese
                        else f" (atom pairs: {pairs})"
                    )
                lines.append(detail)

            if vietnamese:
                lines.append(
                    "\nLưu ý: đây là các tiếp xúc hình học (khoảng cách và cặp "
                    "nguyên tử N/O ≤ 3.5 Å), chưa phải bằng chứng năng lượng "
                    "liên kết hay ái lực gắn."
                )
            else:
                lines.append(
                    "\nNote: these are geometric contacts (distance and N/O atom "
                    "pairs ≤ 3.5 Å), not thermodynamic proof of binding affinity."
                )
            return "\n".join(lines)

        # Fallback to a proximity-only summary if interaction classification failed.
        residues = result.get("residues") or []
        per_instance = result.get("per_instance") or []
        if not residues and not per_instance:
            return None

        if vietnamese:
            lines = [
                f"Các residue lân cận **{resn}** trong `{obj}` "
                f"(cutoff {cutoff} Å): **{len(residues)} residue**."
            ]
        else:
            lines = [
                f"Residues near **{resn}** in `{obj}` "
                f"(cutoff {cutoff} Å): **{len(residues)} residues**."
            ]

        label = "residue" if not vietnamese else "residue"
        if per_instance:
            for item in per_instance:
                t = item.get("target", {})
                ids = [
                    f"{r.get('resn')}{r.get('resi')}" + (
                        f" ({r.get('chain')})" if r.get("chain") else ""
                    )
                    for r in item.get("residues", [])
                ]
                lines.append(
                    f"  - {t.get('resn')} {t.get('resi')}:{t.get('chain')} → "
                    f"{item.get('residue_count', len(ids))} {label}"
                    + (f": {', '.join(ids)}" if ids else "")
                )
        else:
            ids = [
                f"{r.get('resn')}{r.get('resi')}" + (
                    f" ({r.get('chain')})" if r.get("chain") else ""
                )
                for r in residues
            ]
            lines.append("  - " + ", ".join(ids))

        if vietnamese:
            lines.append(
                "\nLưu ý: công cụ phân loại tương tác không chạy được, nên kết quả "
                "chỉ là các residue trong khoảng cách hình học, chưa phân loại "
                "loại tương tác."
            )
        else:
            lines.append(
                "\nNote: interaction classification was unavailable, so this list "
                "only reports geometric proximity and does not classify contact types."
            )
        return "\n".join(lines)

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
        # Last successful tool target, used to resolve follow-up pronouns.
        self._last_focus: Optional[Dict[str, str]] = None

    def cancel(self):
        """Cancel current agent execution."""
        self._cancelled = True
        self.client.cancel()

    def reset_cancellation(self):
        self._cancelled = False
        self.client.reset_cancellation()

    def clear_conversation(self):
        """Clear conversation history and follow-up context."""
        self.conversation_history.clear()
        self._last_focus = None

    def _execute_tool_with_retry(
        self,
        name: str,
        arguments: Dict[str, Any],
        step_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        step_idx: int = 0
    ) -> Dict[str, Any]:
        """Execute a tool, retrying only transient (network) failures.

        Deterministic failures are returned immediately so the agent can adapt
        its strategy. Transient failures are retried a bounded number of times
        with exponential backoff.
        """
        attempt = 0
        while True:
            result = self.registry.execute(name, arguments)
            if result.get("success", False):
                return result

            classification = classify_error(result.get("error", ""))
            if classification != ErrorClassification.TRANSIENT_RETRYABLE:
                return result
            if attempt >= self.TRANSIENT_RETRIES or self._cancelled:
                result["transient_exhausted"] = True
                return result

            delay = self.TRANSIENT_BACKOFF_SECONDS * (2 ** attempt)
            attempt += 1
            if step_callback:
                step_callback({
                    "type": "tool_retry",
                    "step": step_idx,
                    "tool": name,
                    "attempt": attempt,
                    "delay_seconds": delay,
                    "error": result.get("error", "")
                })
            time.sleep(delay)

    def _trim_history(self) -> None:
        """Bound conversation history to the most recent turns.

        A zero/negative limit disables trimming. The oldest kept entry is always
        a user message so the model never starts with an orphaned assistant turn.
        """
        limit = int(CONFIG.max_history_messages)
        if limit <= 0 or len(self.conversation_history) <= limit:
            return

        self.conversation_history = self.conversation_history[-limit:]
        while self.conversation_history and self.conversation_history[0].get("role") != "user":
            self.conversation_history.pop(0)

    @staticmethod
    def _serialize_tool_result(tool_res: Dict[str, Any]) -> str:
        """Serialize a tool result, truncating oversized payloads for the model context."""
        payload = json.dumps(tool_res)
        limit = int(CONFIG.max_tool_result_chars)
        if limit <= 0 or len(payload) <= limit:
            return payload

        return json.dumps({
            "success": tool_res.get("success", False),
            "truncated": True,
            "original_characters": len(payload),
            "preview": payload[:limit],
            "note": "Tool result truncated to protect the model context window."
        })

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
        # Cancellation applies to a single run. Without this reset, one click on
        # "Stop" would permanently make every future instruction return cancelled.
        self.reset_cancellation()
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
        allowed_tool_names: Optional[set] = None

        if matched_wf:
            wf_session = WorkflowSession(matched_wf, entities, intent_match_confidence=confidence)
            wf_session.start()
            # Context-dependent tool scoping: expose and enforce only approved relevant capabilities
            allowed_tool_names = set(matched_wf.required_capabilities or [])
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

        # Ground pronouns and deictic phrases in the last successful action.
        followup_hint = self._followup_focus_hint(user_instruction)
        if followup_hint:
            system_prompt = f"{system_prompt}{followup_hint}"

        # Prepare messages (bounded history prevents context-window blow-up)
        self._trim_history()
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt}
        ]

        # Append previous conversation history for context continuity
        messages.extend(self.conversation_history)

        # Append current user prompt
        messages.append({"role": "user", "content": user_instruction})

        # Also store user instruction in persistent history
        self.conversation_history.append({"role": "user", "content": user_instruction})
        self._trim_history()

        executed_steps: List[AgentStep] = []
        final_answer = ""
        total_start_time = time.time()

        # Track failed tool signatures to prevent infinite retry loops
        failed_signatures: set = set()
        successful_signatures: set = set()
        consecutive_repeated_failures = 0
        early_stopped_due_to_loop = False
        execution_nudge_used = False
        failure_nudge_used = False
        truthfulness_nudge_used = False
        contact_fallback_used = False
        per_instance_fallback_used = False
        run_failed = False

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
            except OllamaConnectionError as e:
                run_failed = True
                error_msg = (
                    f"Cannot reach Ollama at {CONFIG.ollama_host}: {e}. "
                    "Start the Ollama service (`ollama serve` or open the Ollama app), "
                    "then retry."
                )
                final_answer = error_msg
                if step_callback:
                    step_callback({"type": "error", "error": error_msg})
                break
            except OllamaTimeoutError as e:
                run_failed = True
                error_msg = (
                    f"Ollama did not answer within {CONFIG.request_timeout_seconds}s: {e}. "
                    "The first request for a large model can be slow; wait for the model "
                    "to load and retry, or increase `request_timeout_seconds` in the "
                    "Copilot configuration."
                )
                final_answer = error_msg
                if step_callback:
                    step_callback({"type": "error", "error": error_msg})
                break
            except OllamaClientError as e:
                run_failed = True
                raw_error = str(e)
                if "not found" in raw_error.lower() or "http 404" in raw_error.lower():
                    error_msg = (
                        f"Model '{self.model_name}' is not installed in Ollama. "
                        f"Run `ollama pull {self.model_name}` and try again, or choose "
                        "another model from the model selector."
                    )
                else:
                    error_msg = f"LLM communication error: {raw_error}"
                final_answer = error_msg
                if step_callback:
                    step_callback({"type": "error", "error": error_msg})
                break

            step.thinking = response.get("thinking", "")
            step.content = response.get("content", "")
            tool_calls = response.get("tool_calls", [])
            step.duration_ms = round((time.time() - step_start) * 1000, 2)

            # If no tool calls were made, the agent decided it is done or explaining directly
            if not tool_calls:
                # A matched workflow must actually execute. Small local models
                # sometimes reply by restating the recommended plan instead of
                # calling tools; nudge them once with an explicit execution order.
                if matched_wf and not execution_nudge_used and step_idx == 1:
                    execution_nudge_used = True
                    executed_steps.append(step)
                    messages.append({"role": "assistant", "content": step.content})
                    messages.append({
                        "role": "user",
                        "content": (
                            f"Execute workflow {matched_wf.workflow_id} now. "
                            "You must call at least one authorized tool in your next response. "
                            "Do not restate the plan, do not list workflow steps, and do not ask "
                            "the user which step to run. Inspect the current session if needed."
                        )
                    })
                    if step_callback:
                        step_callback({
                            "type": "execution_nudge",
                            "step": step_idx,
                            "workflow_id": matched_wf.workflow_id
                        })
                    continue

                # If every tool call so far failed, do not let the model give up
                # and ask the user to guess a selection. Push it to inspect the
                # error and retry with a corrected argument.
                previous_results = [tr["result"] for s in executed_steps for tr in s.tool_results]
                blocking_failure = any(
                    r.get("non_retryable") or r.get("repeated_failure") or r.get("workflow_scope_violation")
                    for r in previous_results
                )
                if (
                    not failure_nudge_used
                    and previous_results
                    and all(not r.get("success", False) for r in previous_results)
                    and not blocking_failure
                ):
                    failure_nudge_used = True
                    executed_steps.append(step)
                    last_error = str(previous_results[-1].get("error", ""))
                    messages.append({"role": "assistant", "content": step.content})
                    messages.append({
                        "role": "user",
                        "content": (
                            "The previous tool call(s) failed. Do not ask the user to guess a "
                            "residue name or selection. Use the residue names reported in the "
                            "error message, or inspect the session with list_objects / "
                            "get_object_info / get_residues, then retry with corrected "
                            f"arguments. Last error: {last_error}"
                        )
                    })
                    if step_callback:
                        step_callback({
                            "type": "failure_nudge",
                            "step": step_idx,
                            "error": last_error
                        })
                    continue

                # Guard against fabricated scientific results: an actionable
                # request answered without a single successful tool call must
                # not be presented as an analysis result.
                any_success = any(r.get("success", False) for r in previous_results)
                if (
                    not truthfulness_nudge_used
                    and not execution_nudge_used
                    and not failure_nudge_used
                    and not any_success
                    and self._looks_actionable_instruction(user_instruction)
                ):
                    truthfulness_nudge_used = True
                    executed_steps.append(step)
                    messages.append({"role": "assistant", "content": step.content})
                    messages.append({
                        "role": "user",
                        "content": (
                            "Your response did not call any tool, and no tool has succeeded "
                            "in this run. Do not claim that you identified residues, contacts, "
                            "or measurements. If this request needs live PyMOL data, call the "
                            "appropriate tool now (for example get_object_info, "
                            "find_nearby_residues, identify_ligands, or inspect_binding_pocket). "
                            "If it is purely conceptual, state that clearly without inventing "
                            "structure-specific results."
                        )
                    })
                    if step_callback:
                        step_callback({
                            "type": "truthfulness_nudge",
                            "step": step_idx
                        })
                    continue

                # Per-instance requests ("residues for each SO4") must not be
                # answered with a merged list. If the model's answer omits an
                # instance, or reports contact types without per-instance typed
                # data, build the grouped breakdown deterministically.
                typed_analysis_done = any(
                    tr["tool"] == "analyze_ligand_interactions"
                    and tr["result"].get("success", False)
                    for s in executed_steps for tr in s.tool_results
                )
                per_instance_typed_done = any(
                    tr["tool"] == "analyze_ligand_interactions"
                    and tr["result"].get("success", False)
                    and str(tr["result"].get("ligand_resi", ""))
                    for s in executed_steps for tr in s.tool_results
                )
                if (
                    not per_instance_fallback_used
                    and self._wants_per_instance(user_instruction)
                    and self._is_contact_request(user_instruction)
                ):
                    proximity_result = self._last_successful_result(
                        executed_steps, "find_nearby_residues"
                    )
                    needs_instance_breakdown = (
                        not self._answer_covers_instances(step.content, proximity_result)
                    )
                    needs_per_instance_types = (
                        self._wants_contact_types(user_instruction)
                        and not per_instance_typed_done
                    )
                    if needs_instance_breakdown or needs_per_instance_types:
                        per_instance_fallback_used = True
                        fallback = self._deterministic_per_instance_fallback(
                            user_instruction,
                            step,
                            allowed_tool_names,
                            executed_steps,
                            step_callback,
                            step_idx
                        )
                        if fallback:
                            executed_steps.append(step)
                            visual_note = self._ensure_contact_visual_actions(
                                user_instruction,
                                step,
                                allowed_tool_names,
                                executed_steps,
                                step_callback,
                                step_idx
                            )
                            final_answer = (
                                f"{fallback}\n\n{visual_note}" if visual_note else fallback
                            )
                            self.conversation_history.append({
                                "role": "assistant",
                                "content": final_answer
                            })
                            if step_callback:
                                step_callback({
                                    "type": "final_response",
                                    "step": step_idx,
                                    "content": final_answer
                                })
                            break

                # Last line of defense: if the model still refuses to execute a
                # grounded contact request, or answered a contact-type question
                # using proximity-only data, resolve the ligand from the live
                # session and run the analysis in the controller itself.
                missing_contact_types = (
                    self._wants_contact_types(user_instruction)
                    and not typed_analysis_done
                )
                residue_data_done = any(
                    tr["tool"] in (
                        "find_nearby_residues",
                        "analyze_ligand_interactions",
                        "inspect_binding_pocket"
                    )
                    and tr["result"].get("success", False)
                    for s in executed_steps for tr in s.tool_results
                )
                missing_residue_data = (
                    self._wants_residue_list(user_instruction)
                    and not residue_data_done
                )
                if (
                    not contact_fallback_used
                    and self._is_contact_request(user_instruction)
                    and (
                        not any_success
                        or missing_contact_types
                        or missing_residue_data
                    )
                ):
                    contact_fallback_used = True
                    fallback = self._deterministic_contact_fallback(
                        user_instruction,
                        step,
                        allowed_tool_names,
                        step_callback,
                        step_idx
                    )
                    if fallback:
                        executed_steps.append(step)
                        visual_note = self._ensure_contact_visual_actions(
                            user_instruction,
                            step,
                            allowed_tool_names,
                            executed_steps,
                            step_callback,
                            step_idx
                        )
                        final_answer = (
                            f"{fallback}\n\n{visual_note}" if visual_note else fallback
                        )
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": final_answer
                        })
                        if step_callback:
                            step_callback({
                                "type": "final_response",
                                "step": step_idx,
                                "content": final_answer
                            })
                        break

                # If the model only described a requested label/highlight,
                # execute it against the residues already discovered.
                visual_note = self._ensure_contact_visual_actions(
                    user_instruction,
                    step,
                    allowed_tool_names,
                    executed_steps,
                    step_callback,
                    step_idx
                )
                if visual_note:
                    final_answer = (
                        f"{step.content}\n\n{visual_note}" if step.content else visual_note
                    )
                else:
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
                elif (
                    call_sig in successful_signatures
                    and t_name not in self._REPEATABLE_READ_TOOLS
                ):
                    # Small models often get stuck re-running a successful
                    # visualization call because they cannot figure out the
                    # next step. Refuse the duplicate and force progress.
                    consecutive_repeated_failures += 1
                    tool_res = {
                        "success": False,
                        "error": (
                            f"Execution rejected: Tool call '{t_name}' with identical arguments "
                            f"already succeeded in this run. It is not useful to repeat it. "
                            "Continue with the remaining action (for example hide solvent "
                            "with hide_representation(representation='water')), or provide "
                            "the final answer if the request is complete."
                        ),
                        "repeated_success": True,
                        "non_retryable": True,
                    }
                    failed_signatures.add(call_sig)
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
                    elif allowed_tool_names is not None and t_name not in allowed_tool_names:
                        # Workflow-scoped enforcement: the model must not call tools that
                        # were intentionally excluded from the matched workflow.
                        tool_res = {
                            "success": False,
                            "error": (
                                f"Tool '{t_name}' is outside the approved capability scope for "
                                f"workflow '{matched_wf.workflow_id if matched_wf else 'unknown'}'. "
                                f"This is a non-retryable error. Do not call '{t_name}' again. "
                                f"Allowed tools: {sorted(allowed_tool_names)}"
                            ),
                            "non_retryable": True,
                            "workflow_scope_violation": True
                        }
                        failed_signatures.add(call_sig)
                    else:
                        # Execute tool via registry (transient failures retried)
                        tool_res = self._execute_tool_with_retry(t_name, t_args, step_callback, step_idx)
                        if not tool_res.get("success", False):
                            failed_signatures.add(call_sig)
                        else:
                            successful_signatures.add(call_sig)
                            consecutive_repeated_failures = 0  # Reset on successful execution

                step.tool_results.append({
                    "tool": t_name,
                    "arguments": t_args,
                    "result": tool_res
                })

                if tool_res.get("success", False):
                    self._update_followup_focus(t_name, t_args, tool_res)

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
                    "content": self._serialize_tool_result(tool_res)
                })

            executed_steps.append(step)

            # Check if agent is trapped in an unrecoverable failure loop
            if step_has_repeated or consecutive_repeated_failures >= 2:
                early_stopped_due_to_loop = True
                break

        # If max steps reached without final answer, do one final synthesis call
        if not final_answer and not self._cancelled:
            # Before asking the model to synthesize, try the grounded contact
            # fallback when every executed tool failed and the user explicitly
            # asked for residues/interactions.
            fallback_answer: Optional[str] = None
            previous_results = [
                tr["result"] for s in executed_steps for tr in s.tool_results
            ]
            any_prior_success = any(r.get("success", False) for r in previous_results)
            fallback_step = AgentStep(len(executed_steps) + 1)

            if (
                not per_instance_fallback_used
                and self._wants_per_instance(user_instruction)
                and self._is_contact_request(user_instruction)
            ):
                per_instance_fallback_used = True
                fallback_answer = self._deterministic_per_instance_fallback(
                    user_instruction,
                    fallback_step,
                    allowed_tool_names,
                    executed_steps,
                    step_callback,
                    fallback_step.step_number
                )
                if fallback_answer:
                    executed_steps.append(fallback_step)
                elif fallback_step.tool_results:
                    executed_steps.append(fallback_step)

            if (
                not fallback_answer
                and not contact_fallback_used
                and self._is_contact_request(user_instruction)
                and not any_prior_success
            ):
                contact_fallback_used = True
                fallback_answer = self._deterministic_contact_fallback(
                    user_instruction,
                    fallback_step,
                    allowed_tool_names,
                    step_callback,
                    fallback_step.step_number
                )
                if fallback_answer and fallback_step not in executed_steps:
                    executed_steps.append(fallback_step)

            if fallback_answer:
                visual_note = self._ensure_contact_visual_actions(
                    user_instruction,
                    fallback_step,
                    allowed_tool_names,
                    executed_steps,
                    step_callback,
                    fallback_step.step_number
                )
                if visual_note:
                    fallback_answer = f"{fallback_answer}\n\n{visual_note}"
                final_answer = fallback_answer
                self.conversation_history.append({
                    "role": "assistant",
                    "content": final_answer
                })
                if step_callback:
                    step_callback({
                        "type": "final_response",
                        "step": len(executed_steps),
                        "content": final_answer
                    })
            else:
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
                    run_failed = True
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
            "pymol_version": get_pymol_version(),
            "units": {"distances": "angstroms", "angles": "degrees", "rmsd": "angstroms"},
            "tools_executed": [tr["tool"] for s in executed_steps for tr in s.tool_results if tr["result"].get("success")],
            "scientific_limitations": matched_wf.scientific_limitations if matched_wf else []
        }

        # Success determination: do not claim success if execution stopped early due to unrecovered failure
        is_success = not self._cancelled and not run_failed
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
