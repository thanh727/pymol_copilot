"""
Machine-readable CapabilityRegistry for PyMOL Open-Source 3.1.0.

Provides strict allowlist registration, PyMOL API mappings, pre/postcondition verification,
risk tier classification, and exportable machine-readable JSON schemas.

Treats all unreviewed/unimplemented PyMOL APIs as unauthorized for model execution.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from . import tools


class ErrorClassification(str, Enum):
    """Classification of tool execution errors to guide retry policy."""
    DETERMINISTIC_NON_RETRYABLE = "DETERMINISTIC_NON_RETRYABLE"
    TRANSIENT_RETRYABLE = "TRANSIENT_RETRYABLE"
    VALIDATION_FAILURE = "VALIDATION_FAILURE"
    UNAUTHORIZED_TOOL = "UNAUTHORIZED_TOOL"
    CANCELLED = "CANCELLED"


def classify_error(error_msg_or_exc: Any) -> ErrorClassification:
    """
    Classify an execution error to determine whether it can be safely retried.
    Never retry deterministic errors (invalid IDs, unauthorized tools, missing files).
    Only transient network timeouts may be retried.
    """
    if isinstance(error_msg_or_exc, (TimeoutError, ConnectionError)):
        return ErrorClassification.TRANSIENT_RETRYABLE
    msg = str(error_msg_or_exc).lower()
    if "cancelled" in msg:
        return ErrorClassification.CANCELLED
    if "unauthorized" in msg or "not in the authorized" in msg or "not an authorized capability" in msg:
        return ErrorClassification.UNAUTHORIZED_TOOL
    if "precondition failed" in msg or "postcondition failed" in msg or "0 atoms" in msg:
        return ErrorClassification.VALIDATION_FAILURE
    if any(k in msg for k in ["timeout", "timed out", "connection reset", "connection refused", "network", "disconnected", "remote host"]):
        return ErrorClassification.TRANSIENT_RETRYABLE
    return ErrorClassification.DETERMINISTIC_NON_RETRYABLE


@dataclass
class Capability:
    """
    Formal representation of a PyMOL capability.
    Enforces clear security boundaries, API mappings, preconditions, and postconditions.
    """
    id: str                                  # e.g. "io.fetch_structure"
    name: str                                # LLM tool name, e.g. "fetch_structure"
    api_mapping: str                         # e.g. "cmd.fetch"
    category: str                            # Functional domain
    description: str                         # Concise semantic purpose
    parameters: Dict[str, Any]               # JSON Schema for input arguments
    return_schema: Dict[str, Any]            # Expected return structure schema
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    classification: str = "read_only"        # "read_only", "view_only", "io_write", "structural_mutation", "blocked"
    risk_level: str = "Tier A (read-only)"   # "Tier A", "Tier B", "Tier C", "Tier D", "Tier X"
    requires_confirmation: bool = False
    runtime_available: bool = True
    supported_pymol_version: str = ">=2.5, confirmed 3.1.0"
    status: str = "implemented/tested"       # "implemented/tested", "candidate", "unreviewed_unauthorized", "blocked"
    func: Optional[Callable[..., Dict[str, Any]]] = None

    def is_authorized(self) -> bool:
        """Only explicitly implemented and tested tools with registered callables are authorized."""
        return self.status == "implemented/tested" and self.func is not None

    def to_ollama_format(self) -> Dict[str, Any]:
        """Convert to Ollama / OpenAI native tool schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary (excluding callable)."""
        d = asdict(self)
        d.pop("func", None)
        d["is_authorized"] = self.is_authorized()
        return d


class CapabilityRegistry:
    """
    Central repository of PyMOL capabilities.
    Distinguishes runtime-discovered APIs from authorized LLM tools.
    """

    def __init__(self, inventory_path: Optional[str] = None):
        self._capabilities: Dict[str, Capability] = {}
        self._name_to_id: Dict[str, str] = {}
        self._register_implemented_tools()

        # Optionally import discovered API inventory to catalog unreviewed/blocked entries
        inv_file = inventory_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "pymol_inventory", "pymol_api_inventory.json"
        )
        if os.path.exists(inv_file):
            self.load_inventory(inv_file)

    def register(self, cap: Capability) -> None:
        """Register a capability into the catalog."""
        self._capabilities[cap.id] = cap
        self._name_to_id[cap.name] = cap.id

    def get(self, id_or_name: str) -> Optional[Capability]:
        """Retrieve capability by canonical ID or LLM tool name."""
        if id_or_name in self._capabilities:
            return self._capabilities[id_or_name]
        if id_or_name in self._name_to_id:
            return self._capabilities[self._name_to_id[id_or_name]]
        return None

    def is_authorized(self, id_or_name: str) -> bool:
        """Check whether a capability is authorized for autonomous model execution."""
        cap = self.get(id_or_name)
        return cap.is_authorized() if cap else False

    def list_capabilities(
        self,
        category: Optional[str] = None,
        authorized_only: bool = True
    ) -> List[Capability]:
        """List capabilities matching criteria."""
        caps = list(self._capabilities.values())
        if authorized_only:
            caps = [c for c in caps if c.is_authorized()]
        if category:
            caps = [c for c in caps if c.category.lower().startswith(category.lower())]
        return sorted(caps, key=lambda c: c.name)

    def list_authorized_tools(self) -> List[Capability]:
        """Return all authorized LLM-facing tools."""
        return [c for c in self._capabilities.values() if c.is_authorized()]

    def get_ollama_tools(self, subset: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Return Ollama JSON schemas for authorized tools.
        If subset is specified, scopes tools to that subset (context-dependent tool selection).
        """
        if subset:
            subset_set = set(subset)
            return [
                c.to_ollama_format()
                for c in self._capabilities.values()
                if c.is_authorized() and (c.name in subset_set or c.id in subset_set)
            ]
        return [c.to_ollama_format() for c in self._capabilities.values() if c.is_authorized()]

    def verify_preconditions(self, cap: Capability, arguments: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Verify preconditions before executing a capability."""
        from pymol import cmd

        for pre in cap.preconditions:
            if pre == "valid_pdb_id":
                import re
                pid = arguments.get("pdb_id", "")
                if not re.match(r"^(?:pdb_)?[0-9][a-z0-9]{3}$", pid.strip().lower()) and not re.match(r"^af-[a-z0-9]+-f\d+", pid.strip().lower()):
                    return False, f"Precondition failed: Invalid PDB ID format '{pid}'"
            elif pre == "local_file_exists":
                fpath = arguments.get("file_path", "")
                if not fpath or not os.path.exists(os.path.expanduser(fpath)):
                    return False, f"Precondition failed: File does not exist '{fpath}'"
            elif pre == "objects_exist":
                objs = cmd.get_names("objects")
                if not objs:
                    return False, "Precondition failed: No molecular objects are loaded in PyMOL"
            elif pre == "two_or_more_objects":
                objs = cmd.get_names("objects")
                if len(objs) < 2:
                    return False, f"Precondition failed: Requires at least 2 loaded objects for comparison (found {len(objs)})"
            elif pre == "valid_selection":
                sel = arguments.get("selection") or arguments.get("mobile_selection") or arguments.get("target_selection")
                if sel and cmd.count_atoms(sel) == 0:
                    # Provide informative feedback
                    pass
        return True, None

    def verify_postconditions(self, cap: Capability, result: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Verify postconditions after executing a capability."""
        from pymol import cmd

        if not result.get("success", False):
            return True, None  # Failure was already captured

        for post in cap.postconditions:
            if post == "object_exists":
                obj_name = result.get("object_name")
                if obj_name and obj_name not in cmd.get_names("all"):
                    return False, f"Postcondition failed: Object '{obj_name}' was not created in PyMOL"
            elif post == "atom_count_gt_zero":
                count = result.get("atom_count", 0)
                if count <= 0:
                    return False, "Postcondition failed: Created object contains 0 atoms"
            elif post == "file_created":
                out_path = result.get("file_path") or result.get("output_path") or result.get("image_path") or result.get("filepath") or result.get("filename")
                if out_path and not os.path.exists(out_path):
                    return False, f"Postcondition failed: Expected output file was not created '{out_path}'"
        return True, None

    def execute(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute tool with whitelist validation, schema pre-checking, and postcondition verification.
        """
        cap = self.get(name)
        if not cap or not cap.is_authorized():
            auth_names = [c.name for c in self.list_authorized_tools()]
            return {
                "success": False,
                "error": (
                    f"Tool '{name}' is not an authorized capability. "
                    f"All unreviewed PyMOL APIs default to LLM-disallowed. "
                    f"Available authorized capabilities: {auth_names}"
                ),
                "unauthorized": True,
                "non_retryable": True
            }

        # 1. Verify preconditions
        pre_ok, pre_err = self.verify_preconditions(cap, arguments)
        if not pre_ok:
            return {
                "success": False,
                "error": pre_err,
                "precondition_failure": True
            }

        # Normalize common parameter aliases
        norm_args = dict(arguments)
        if name in ("export_png", "save_session", "export_pml", "export_analysis_json", "export_analysis_csv"):
            if "output_path" in norm_args and "filename" not in norm_args:
                norm_args["filename"] = norm_args.pop("output_path")
            elif "file_path" in norm_args and "filename" not in norm_args:
                norm_args["filename"] = norm_args.pop("file_path")
        elif name == "analyze_mutation":
            if "mutation_notation" in norm_args and "mutation_str" not in norm_args:
                norm_args["mutation_str"] = norm_args.pop("mutation_notation")
            elif "mutation" in norm_args and "mutation_str" not in norm_args:
                norm_args["mutation_str"] = norm_args.pop("mutation")
            if "cutoff" in norm_args and "radius" not in norm_args:
                norm_args["radius"] = norm_args.pop("cutoff")
        elif name == "label_residues":
            if "label" in norm_args and "label_type" not in norm_args:
                norm_args["label_type"] = norm_args.pop("label")

        # 2. Execute underlying verified adapter
        try:
            res = cap.func(**norm_args)
            if not isinstance(res, dict):
                res = {"success": True, "result": res}
            if "success" not in res:
                res["success"] = True
        except TypeError as e:
            return {
                "success": False,
                "error": f"Invalid arguments provided for capability '{cap.name}': {e}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Capability execution failed for '{cap.name}': {e}"
            }

        # 3. Verify postconditions
        post_ok, post_err = self.verify_postconditions(cap, res)
        if not post_ok:
            res["success"] = False
            res["error"] = post_err
            res["postcondition_failure"] = True
            return res

        # 4. Attach metadata and provenance
        res["provenance"] = {
            "capability_id": cap.id,
            "api_mapping": cap.api_mapping,
            "risk_level": cap.risk_level,
            "verified": True
        }
        return res

    def export_capabilities_json(self, output_path: Path | str) -> None:
        """Export the full machine-readable capability registry to a JSON file."""
        data = {
            "metadata": {
                "registry": "PyMOL AI Copilot Capability Registry",
                "total_capabilities": len(self._capabilities),
                "authorized_capabilities": len(self.list_authorized_tools()),
                "unreviewed_capabilities": len([c for c in self._capabilities.values() if c.status == "unreviewed_unauthorized"]),
                "blocked_capabilities": len([c for c in self._capabilities.values() if c.status == "blocked"]),
            },
            "capabilities": [c.to_dict() for c in sorted(self._capabilities.values(), key=lambda c: c.id)]
        }
        Path(output_path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def load_inventory(self, inventory_json_path: str) -> None:
        """
        Ingest the runtime API inventory.
        All entries not currently implemented as authorized tools are marked as
        'unreviewed_unauthorized' (or 'blocked' if Tier X) and given func=None.
        """
        try:
            with open(inventory_json_path, "r", encoding="utf-8") as f:
                inv = json.load(f)
            for entry in inv.get("entries", []):
                p_name = entry["name"]
                if p_name in self._name_to_id:
                    # Already implemented and authorized
                    continue

                is_blocked = "blocked" in entry.get("risk_policy", "").lower()
                status = "blocked" if is_blocked else "unreviewed_unauthorized"
                risk = "Tier X (blocked)" if is_blocked else "Unreviewed"

                cap = Capability(
                    id=f"pymol_raw.{p_name}",
                    name=p_name,
                    api_mapping=f"cmd.{p_name}" if entry.get("in_python_api") else f"pml:{p_name}",
                    category=entry.get("primary_category", "99 Uncategorized / review"),
                    description=entry.get("description", f"Discovered PyMOL API '{p_name}' (unauthorized)"),
                    parameters={"type": "object", "properties": {}, "description": "Raw unvetted parameters."},
                    return_schema={"type": "object"},
                    classification="blocked" if is_blocked else "unreviewed",
                    risk_level=risk,
                    requires_confirmation=True,
                    runtime_available=True,
                    status=status,
                    func=None
                )
                self._capabilities[cap.id] = cap
        except Exception:
            pass  # Non-fatal if inventory is absent or malformed

    def _register_implemented_tools(self) -> None:
        """Register the 35 verified, typed, and tested Copilot tools."""

        # --------------------------------------------------------------------
        # 01 Input, retrieval, files
        # --------------------------------------------------------------------
        self.register(Capability(
            id="io.fetch_structure",
            name="fetch_structure",
            api_mapping="cmd.fetch",
            category="01 Input, retrieval, files",
            description="Download and load a structure from the Protein Data Bank (PDB) into PyMOL. Use for PDB accession codes (e.g. '1ubq', '1ake') or AlphaFold IDs.",
            parameters={
                "type": "object",
                "properties": {
                    "pdb_id": {"type": "string", "description": "Standard 4-character PDB ID (e.g. '1ubq') or AlphaFold accession."},
                    "object_name": {"type": "string", "description": "Optional custom name for the loaded object."},
                    "format": {"type": "string", "description": "File format: 'cif' (default) or 'pdb'.", "enum": ["cif", "pdb"]}
                },
                "required": ["pdb_id"]
            },
            return_schema={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string"},
                    "atom_count": {"type": "integer"},
                    "chains": {"type": "array", "items": {"type": "string"}},
                    "ligands": {"type": "array"}
                }
            },
            preconditions=["valid_pdb_id"],
            postconditions=["object_exists", "atom_count_gt_zero"],
            classification="io_write",
            risk_level="Tier C (bounded I/O)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_fetch_structure
        ))

        self.register(Capability(
            id="io.load_structure",
            name="load_structure",
            api_mapping="cmd.load",
            category="01 Input, retrieval, files",
            description="Load a molecular structure from a local filesystem path (PDB, mmCIF, mol2, sdf).",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Local path to the molecular structure file."},
                    "object_name": {"type": "string", "description": "Optional name for loaded object."}
                },
                "required": ["file_path"]
            },
            return_schema={"type": "object", "properties": {"object_name": {"type": "string"}, "atom_count": {"type": "integer"}}},
            preconditions=["local_file_exists"],
            postconditions=["object_exists", "atom_count_gt_zero"],
            classification="io_write",
            risk_level="Tier C (bounded I/O)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_load_structure
        ))

        self.register(Capability(
            id="io.save_session",
            name="save_session",
            api_mapping="cmd.save",
            category="01 Input, retrieval, files",
            description="Save the entire current PyMOL session state to a .pse file.",
            parameters={
                "type": "object",
                "properties": {"file_path": {"type": "string", "description": "Output path for the .pse session file."}},
                "required": ["file_path"]
            },
            return_schema={"type": "object", "properties": {"file_path": {"type": "string"}}},
            preconditions=["objects_exist"],
            postconditions=["file_created"],
            classification="io_write",
            risk_level="Tier C (bounded I/O)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_save_session
        ))

        self.register(Capability(
            id="io.export_png",
            name="export_png",
            api_mapping="cmd.png",
            category="01 Input, retrieval, files",
            description="Render and export a high-resolution PNG image of the current PyMOL 3D view with optional ray-tracing.",
            parameters={
                "type": "object",
                "properties": {
                    "output_path": {"type": "string", "description": "File path where PNG image will be saved."},
                    "width": {"type": "integer", "description": "Image width in pixels (default 1920)."},
                    "height": {"type": "integer", "description": "Image height in pixels (default 1080)."},
                    "ray": {"type": "boolean", "description": "Whether to ray-trace (default true)."}
                },
                "required": ["output_path"]
            },
            return_schema={"type": "object", "properties": {"output_path": {"type": "string"}, "dimensions": {"type": "string"}}},
            preconditions=[],
            postconditions=["file_created"],
            classification="io_write",
            risk_level="Tier C (bounded I/O)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_export_png
        ))

        self.register(Capability(
            id="io.export_pml",
            name="export_pml",
            api_mapping="executor.get_pml_script",
            category="01 Input, retrieval, files",
            description="Export all operations executed during the session as a reproducible PyMOL command script (.pml).",
            parameters={
                "type": "object",
                "properties": {"output_path": {"type": "string", "description": "Output path for .pml script."}},
                "required": ["output_path"]
            },
            return_schema={"type": "object", "properties": {"output_path": {"type": "string"}, "command_count": {"type": "integer"}}},
            preconditions=[],
            postconditions=["file_created"],
            classification="io_write",
            risk_level="Tier C (bounded I/O)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_export_pml
        ))

        self.register(Capability(
            id="io.export_analysis_json",
            name="export_analysis_json",
            api_mapping="json.dump",
            category="01 Input, retrieval, files",
            description="Save structured scientific data (e.g. RMSD, contacts, pocket residues) to a JSON file.",
            parameters={
                "type": "object",
                "properties": {
                    "data": {"type": "object", "description": "Structured data to save."},
                    "output_path": {"type": "string", "description": "Output path for JSON file."}
                },
                "required": ["data", "output_path"]
            },
            return_schema={"type": "object", "properties": {"output_path": {"type": "string"}}},
            preconditions=[],
            postconditions=["file_created"],
            classification="io_write",
            risk_level="Tier C (bounded I/O)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_export_analysis_json
        ))

        self.register(Capability(
            id="io.export_analysis_csv",
            name="export_analysis_csv",
            api_mapping="csv.DictWriter",
            category="01 Input, retrieval, files",
            description="Save tabular analysis rows (e.g. residue contacts or mutations) to a CSV file.",
            parameters={
                "type": "object",
                "properties": {
                    "rows": {"type": "array", "description": "List of row dictionaries."},
                    "output_path": {"type": "string", "description": "Output path for CSV file."}
                },
                "required": ["rows", "output_path"]
            },
            return_schema={"type": "object", "properties": {"output_path": {"type": "string"}}},
            preconditions=[],
            postconditions=["file_created"],
            classification="io_write",
            risk_level="Tier C (bounded I/O)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_export_analysis_csv
        ))

        # --------------------------------------------------------------------
        # 02 Object and session management
        # --------------------------------------------------------------------
        self.register(Capability(
            id="session.list_objects",
            name="list_objects",
            api_mapping="cmd.get_names",
            category="02 Object and session management",
            description="List all molecular objects and active selections currently loaded in PyMOL.",
            parameters={"type": "object", "properties": {}, "required": []},
            return_schema={"type": "object", "properties": {"objects": {"type": "array"}, "count": {"type": "integer"}}},
            preconditions=[],
            postconditions=[],
            classification="read_only",
            risk_level="Tier A (read-only)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_list_objects
        ))

        # --------------------------------------------------------------------
        # 03 Structure inspection
        # --------------------------------------------------------------------
        self.register(Capability(
            id="inspect.get_chains",
            name="get_chains",
            api_mapping="cmd.get_chains",
            category="03 Structure inspection",
            description="Get the list of chains for loaded objects in PyMOL.",
            parameters={
                "type": "object",
                "properties": {"object_name": {"type": "string", "description": "Optional object name."}},
                "required": []
            },
            return_schema={"type": "object", "properties": {"chains": {"type": "object"}}},
            preconditions=["objects_exist"],
            postconditions=[],
            classification="read_only",
            risk_level="Tier A (read-only)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_get_chains
        ))

        self.register(Capability(
            id="inspect.count_atoms",
            name="count_atoms",
            api_mapping="cmd.count_atoms",
            category="03 Structure inspection",
            description="Count the total number of atoms matching a PyMOL selection expression.",
            parameters={
                "type": "object",
                "properties": {"selection": {"type": "string", "description": "PyMOL selection expression."}},
                "required": ["selection"]
            },
            return_schema={"type": "object", "properties": {"atom_count": {"type": "integer"}}},
            preconditions=[],
            postconditions=[],
            classification="read_only",
            risk_level="Tier A (read-only)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_count_atoms
        ))

        self.register(Capability(
            id="inspect.get_residues",
            name="get_residues",
            api_mapping="cmd.iterate",
            category="03 Structure inspection",
            description="Get the sequence of residues (resn, resi, chain) in a protein or chain.",
            parameters={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string", "description": "Object name."},
                    "chain": {"type": "string", "description": "Chain identifier."}
                },
                "required": []
            },
            return_schema={"type": "object", "properties": {"residues": {"type": "array"}, "count": {"type": "integer"}}},
            preconditions=["objects_exist"],
            postconditions=[],
            classification="read_only",
            risk_level="Tier A (read-only)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_get_residues
        ))

        self.register(Capability(
            id="inspect.get_selection_info",
            name="get_selection_info",
            api_mapping="cmd.iterate",
            category="03 Structure inspection",
            description="Get atom count, residue count, and chains for any PyMOL selection expression.",
            parameters={
                "type": "object",
                "properties": {"selection": {"type": "string", "description": "PyMOL selection expression."}},
                "required": ["selection"]
            },
            return_schema={"type": "object", "properties": {"atom_count": {"type": "integer"}, "residue_count": {"type": "integer"}}},
            preconditions=[],
            postconditions=[],
            classification="read_only",
            risk_level="Tier A (read-only)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_get_selection_info
        ))

        self.register(Capability(
            id="inspect.get_object_info",
            name="get_object_info",
            api_mapping="cmd.count_atoms + cmd.get_extent",
            category="03 Structure inspection",
            description="Get structural statistics for an object: total atoms, protein/nucleic/ligand atoms, chains, bounding box, dimensions.",
            parameters={
                "type": "object",
                "properties": {"object_name": {"type": "string", "description": "Name of object to inspect."}},
                "required": ["object_name"]
            },
            return_schema={"type": "object", "properties": {"total_atoms": {"type": "integer"}, "chains": {"type": "array"}, "ligands": {"type": "array"}}},
            preconditions=["objects_exist"],
            postconditions=[],
            classification="read_only",
            risk_level="Tier A (read-only)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_get_object_info
        ))

        self.register(Capability(
            id="inspect.get_structure_summary",
            name="get_structure_summary",
            api_mapping="composite inspection",
            category="03 Structure inspection",
            description="Get a complete overview of all loaded objects, chains, ligands, and active selections.",
            parameters={"type": "object", "properties": {}, "required": []},
            return_schema={"type": "object", "properties": {"summary": {"type": "object"}}},
            preconditions=[],
            postconditions=[],
            classification="read_only",
            risk_level="Tier A (read-only)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_get_structure_summary
        ))

        # --------------------------------------------------------------------
        # 04 Selection and atom queries
        # --------------------------------------------------------------------
        self.register(Capability(
            id="selection.select_residues",
            name="select_residues",
            api_mapping="cmd.select",
            category="04 Selection and atom queries",
            description="Create a named selection in PyMOL for future reference (e.g. name='ligand_pocket', selection='organic around 5').",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name for the created selection."},
                    "selection": {"type": "string", "description": "PyMOL selection expression."}
                },
                "required": ["name", "selection"]
            },
            return_schema={"type": "object", "properties": {"selection_name": {"type": "string"}, "atom_count": {"type": "integer"}}},
            preconditions=[],
            postconditions=[],
            classification="view_only",
            risk_level="Tier B (visual)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_select_residues
        ))

        # --------------------------------------------------------------------
        # 05 Representation and color
        # --------------------------------------------------------------------
        self.register(Capability(
            id="view.show_representation",
            name="show_representation",
            api_mapping="cmd.show",
            category="05 Representation and color",
            description="Show a 3D molecular representation for a selection (cartoon, sticks, spheres, surface, lines, ribbon, etc.).",
            parameters={
                "type": "object",
                "properties": {
                    "representation": {
                        "type": "string",
                        "description": "Representation to show.",
                        "enum": ["cartoon", "sticks", "spheres", "surface", "ribbon", "lines", "mesh", "dots", "nonbonded", "nb_spheres"]
                    },
                    "selection": {"type": "string", "description": "PyMOL selection expression (default 'all')."}
                },
                "required": ["representation"]
            },
            return_schema={"type": "object", "properties": {"representation": {"type": "string"}, "atom_count": {"type": "integer"}}},
            preconditions=[],
            postconditions=[],
            classification="view_only",
            risk_level="Tier B (visual)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_show_representation
        ))

        self.register(Capability(
            id="view.hide_representation",
            name="hide_representation",
            api_mapping="cmd.hide",
            category="05 Representation and color",
            description="Hide a molecular representation (e.g. 'everything', 'cartoon', 'lines', 'sticks', 'surface').",
            parameters={
                "type": "object",
                "properties": {
                    "representation": {"type": "string", "description": "Representation to hide (default 'everything')."},
                    "selection": {"type": "string", "description": "PyMOL selection expression (default 'all')."}
                },
                "required": []
            },
            return_schema={"type": "object", "properties": {"representation": {"type": "string"}}},
            preconditions=[],
            postconditions=[],
            classification="view_only",
            risk_level="Tier B (visual)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_hide_representation
        ))

        self.register(Capability(
            id="view.color_selection",
            name="color_selection",
            api_mapping="cmd.color",
            category="05 Representation and color",
            description="Apply color to a selection. Supports color names ('marine', 'red'), 'rainbow', 'by_chain', or 'secondary_structure'.",
            parameters={
                "type": "object",
                "properties": {
                    "color": {"type": "string", "description": "Color name or scheme ('by_chain', 'secondary_structure', 'rainbow')."},
                    "selection": {"type": "string", "description": "PyMOL selection expression (default 'all')."}
                },
                "required": ["color"]
            },
            return_schema={"type": "object", "properties": {"color": {"type": "string"}, "selection": {"type": "string"}}},
            preconditions=[],
            postconditions=[],
            classification="view_only",
            risk_level="Tier B (visual)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_color_selection
        ))

        self.register(Capability(
            id="view.highlight_residues",
            name="highlight_residues",
            api_mapping="cmd.show + cmd.color",
            category="05 Representation and color",
            description="Highlight specific residues with a chosen representation (e.g. 'sticks') and distinct color.",
            parameters={
                "type": "object",
                "properties": {
                    "selection": {"type": "string", "description": "PyMOL selection expression for residues."},
                    "representation": {"type": "string", "description": "Representation to display (default 'sticks')."},
                    "color": {"type": "string", "description": "Highlight color (default 'yellow')."}
                },
                "required": ["selection"]
            },
            return_schema={"type": "object", "properties": {"highlighted_selection": {"type": "string"}, "atom_count": {"type": "integer"}}},
            preconditions=[],
            postconditions=[],
            classification="view_only",
            risk_level="Tier B (visual)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_highlight_residues
        ))

        self.register(Capability(
            id="view.set_transparency",
            name="set_transparency",
            api_mapping="cmd.set transparency",
            category="05 Representation and color",
            description="Set surface or cartoon transparency between 0.0 (opaque) and 1.0 (invisible).",
            parameters={
                "type": "object",
                "properties": {
                    "value": {"type": "number", "description": "Transparency value from 0.0 to 1.0."},
                    "selection": {"type": "string", "description": "Target selection (default 'all')."},
                    "mode": {"type": "string", "description": "Type: 'surface' or 'cartoon' (default 'surface').", "enum": ["surface", "cartoon"]}
                },
                "required": ["value"]
            },
            return_schema={"type": "object", "properties": {"transparency": {"type": "number"}}},
            preconditions=[],
            postconditions=[],
            classification="view_only",
            risk_level="Tier B (visual)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_set_transparency
        ))

        self.register(Capability(
            id="view.label_residues",
            name="label_residues",
            api_mapping="cmd.label",
            category="05 Representation and color",
            description="Add 3D text labels to residues in PyMOL (e.g. 'resn_resi' for 'ARG132', 'resi' for '132').",
            parameters={
                "type": "object",
                "properties": {
                    "selection": {"type": "string", "description": "Selection of residues to label."},
                    "label_format": {"type": "string", "description": "Label format: 'resn_resi', 'resi', 'resn', 'name', 'clear'.", "enum": ["resn_resi", "resi", "resn", "name", "clear"]}
                },
                "required": ["selection"]
            },
            return_schema={"type": "object", "properties": {"label_format": {"type": "string"}}},
            preconditions=[],
            postconditions=[],
            classification="view_only",
            risk_level="Tier B (visual)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_label_residues
        ))

        self.register(Capability(
            id="view.apply_visualization_preset",
            name="apply_visualization_preset",
            api_mapping="composite presets",
            category="05 Representation and color",
            description="Apply a coordinated publication preset: 'cartoon_by_chain', 'binding_pocket', 'mutation_neighborhood', or 'epitope'.",
            parameters={
                "type": "object",
                "properties": {
                    "preset_name": {"type": "string", "description": "Preset name.", "enum": ["cartoon_by_chain", "binding_pocket", "mutation_neighborhood", "epitope"]},
                    "target_selection": {"type": "string", "description": "Target selection or ligand/mutation/epitope selection."},
                    "cutoff": {"type": "number", "description": "Pocket or neighborhood radius in angstroms (default 5.0)."}
                },
                "required": ["preset_name"]
            },
            return_schema={"type": "object", "properties": {"preset_applied": {"type": "string"}}},
            preconditions=[],
            postconditions=[],
            classification="view_only",
            risk_level="Tier B (visual)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_apply_visualization_preset
        ))

        # --------------------------------------------------------------------
        # 06 Camera and viewport
        # --------------------------------------------------------------------
        self.register(Capability(
            id="camera.orient_selection",
            name="orient_selection",
            api_mapping="cmd.orient",
            category="06 Camera and viewport",
            description="Orient the camera along the principal axes of the given selection.",
            parameters={
                "type": "object",
                "properties": {"selection": {"type": "string", "description": "Selection to orient (default 'all')."}},
                "required": []
            },
            return_schema={"type": "object", "properties": {"selection": {"type": "string"}}},
            preconditions=[],
            postconditions=[],
            classification="view_only",
            risk_level="Tier B (visual)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_orient_selection
        ))

        self.register(Capability(
            id="camera.zoom_selection",
            name="zoom_selection",
            api_mapping="cmd.zoom",
            category="06 Camera and viewport",
            description="Center and zoom the camera onto a selection with optional padding buffer.",
            parameters={
                "type": "object",
                "properties": {
                    "selection": {"type": "string", "description": "Selection to focus on (default 'all')."},
                    "buffer": {"type": "number", "description": "Border buffer in angstroms (default 2.0)."}
                },
                "required": []
            },
            return_schema={"type": "object", "properties": {"selection": {"type": "string"}}},
            preconditions=[],
            postconditions=[],
            classification="view_only",
            risk_level="Tier B (visual)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_zoom_selection
        ))

        self.register(Capability(
            id="camera.reset_view",
            name="reset_view",
            api_mapping="cmd.reset",
            category="06 Camera and viewport",
            description="Reset the 3D viewport camera to the initial default orientation.",
            parameters={"type": "object", "properties": {}, "required": []},
            return_schema={"type": "object", "properties": {"reset": {"type": "boolean"}}},
            preconditions=[],
            postconditions=[],
            classification="view_only",
            risk_level="Tier B (visual)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_reset_view
        ))

        self.register(Capability(
            id="camera.set_background",
            name="set_background",
            api_mapping="cmd.bg_color",
            category="06 Camera and viewport",
            description="Set the background color of the PyMOL 3D viewport (e.g. 'white', 'black', 'grey80').",
            parameters={
                "type": "object",
                "properties": {"color": {"type": "string", "description": "Color name (e.g. 'white', 'black')."}},
                "required": ["color"]
            },
            return_schema={"type": "object", "properties": {"background_color": {"type": "string"}}},
            preconditions=[],
            postconditions=[],
            classification="view_only",
            risk_level="Tier B (visual)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_set_background
        ))

        # --------------------------------------------------------------------
        # 07 Distances and geometry
        # --------------------------------------------------------------------
        self.register(Capability(
            id="geometry.calculate_distances",
            name="calculate_distances",
            api_mapping="cmd.distance + numpy",
            category="07 Distances and geometry",
            description="Calculate pairwise atomic distances between two selections within a distance cutoff.",
            parameters={
                "type": "object",
                "properties": {
                    "selection1": {"type": "string", "description": "First selection."},
                    "selection2": {"type": "string", "description": "Second selection."},
                    "cutoff": {"type": "number", "description": "Maximum distance cutoff in angstroms (default 5.0)."}
                },
                "required": ["selection1", "selection2"]
            },
            return_schema={"type": "object", "properties": {"min_distance_angstrom": {"type": "number"}, "contact_pairs_count": {"type": "integer"}}},
            preconditions=[],
            postconditions=[],
            classification="read_only",
            risk_level="Tier A (read-only)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_calculate_distances
        ))

        self.register(Capability(
            id="geometry.find_nearby_residues",
            name="find_nearby_residues",
            api_mapping="cmd.iterate + selection",
            category="07 Distances and geometry",
            description="Find all polymer residues within cutoff angstroms of a target selection (e.g. 'organic', 'resn AP5', 'resi 50').",
            parameters={
                "type": "object",
                "properties": {
                    "target_selection": {"type": "string", "description": "Target selection expression."},
                    "cutoff": {"type": "number", "description": "Distance radius in angstroms (default 5.0)."},
                    "surrounding_scope": {"type": "string", "description": "Scope of surrounding search (default 'polymer')."}
                },
                "required": ["target_selection"]
            },
            return_schema={"type": "object", "properties": {"residue_count": {"type": "integer"}, "residues": {"type": "array"}}},
            preconditions=[],
            postconditions=[],
            classification="read_only",
            risk_level="Tier A (read-only)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_find_nearby_residues
        ))

        self.register(Capability(
            id="geometry.find_polar_contact_candidates",
            name="find_polar_contact_candidates",
            api_mapping="cmd.distance + geometry",
            category="07 Distances and geometry",
            description="Identify geometric polar contact candidates (donor-acceptor atom pairs <= 3.5 Å). Note: geometric candidates, not confirmed H-bonds.",
            parameters={
                "type": "object",
                "properties": {
                    "selection1": {"type": "string", "description": "First selection."},
                    "selection2": {"type": "string", "description": "Second selection."},
                    "cutoff": {"type": "number", "description": "Maximum distance in angstroms (default 3.5)."}
                },
                "required": ["selection1", "selection2"]
            },
            return_schema={"type": "object", "properties": {"polar_contact_candidates_count": {"type": "integer"}, "pairs": {"type": "array"}}},
            preconditions=[],
            postconditions=[],
            classification="read_only",
            risk_level="Tier A (read-only)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_find_polar_contact_candidates
        ))

        self.register(Capability(
            id="geometry.inspect_binding_pocket",
            name="inspect_binding_pocket",
            api_mapping="composite pocket inspection",
            category="07 Distances and geometry",
            description="Analyze a ligand binding pocket: identifies pocket residues, classifies hydrophobic, polar, and aromatic residues.",
            parameters={
                "type": "object",
                "properties": {
                    "ligand_selection": {"type": "string", "description": "Selection for the ligand (e.g. 'organic' or 'resn AP5')."},
                    "cutoff": {"type": "number", "description": "Pocket definition radius in angstroms (default 5.0)."},
                    "protein_object": {"type": "string", "description": "Optional protein object name."}
                },
                "required": ["ligand_selection"]
            },
            return_schema={"type": "object", "properties": {"pocket_residues_count": {"type": "integer"}, "residues": {"type": "array"}}},
            preconditions=[],
            postconditions=[],
            classification="read_only",
            risk_level="Tier A (read-only)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_inspect_binding_pocket
        ))

        # --------------------------------------------------------------------
        # 08 Structure alignment
        # --------------------------------------------------------------------
        self.register(Capability(
            id="align.align_structures",
            name="align_structures",
            api_mapping="cmd.align / super / cealign",
            category="08 Structure alignment",
            description="Superimpose mobile structure onto target reference and calculate RMSD. Methods: 'align', 'super', 'cealign'.",
            parameters={
                "type": "object",
                "properties": {
                    "mobile": {"type": "string", "description": "Name of object to align."},
                    "target": {"type": "string", "description": "Name of reference structure."},
                    "method": {"type": "string", "description": "Method: 'align', 'super', 'cealign'.", "enum": ["align", "super", "cealign"]},
                    "cutoff": {"type": "number", "description": "Outlier rejection cutoff in angstroms (default 2.0)."},
                    "cycles": {"type": "integer", "description": "Max refinement cycles (default 5)."}
                },
                "required": ["mobile", "target"]
            },
            return_schema={"type": "object", "properties": {"rmsd_post_refinement": {"type": "number"}, "aligned_atoms": {"type": "integer"}}},
            preconditions=["two_or_more_objects"],
            postconditions=[],
            classification="read_only",
            risk_level="Tier A (read-only)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_align_structures
        ))

        self.register(Capability(
            id="align.calculate_rmsd",
            name="calculate_rmsd",
            api_mapping="cmd.rms_cur / cmd.align",
            category="08 Structure alignment",
            description="Calculate RMSD between two selections with explicit atom filtering ('CA', 'backbone', or 'all').",
            parameters={
                "type": "object",
                "properties": {
                    "mobile_selection": {"type": "string", "description": "Mobile selection."},
                    "target_selection": {"type": "string", "description": "Target selection."},
                    "atom_type": {"type": "string", "description": "Atom filter: 'CA', 'backbone', 'all'.", "enum": ["CA", "backbone", "all"]},
                    "align_first": {"type": "boolean", "description": "Whether to superimpose before calculating RMSD (default false)."}
                },
                "required": ["mobile_selection", "target_selection"]
            },
            return_schema={"type": "object", "properties": {"rmsd_angstrom": {"type": "number"}, "atom_count": {"type": "integer"}}},
            preconditions=["two_or_more_objects"],
            postconditions=[],
            classification="read_only",
            risk_level="Tier A (read-only)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_calculate_rmsd
        ))

        self.register(Capability(
            id="align.compare_residues",
            name="compare_residues",
            api_mapping="numpy coordinate delta",
            category="08 Structure alignment",
            description="Identify residue positions with structural divergence (Cα distance > threshold Å) between two aligned structures.",
            parameters={
                "type": "object",
                "properties": {
                    "object1": {"type": "string", "description": "First object name."},
                    "object2": {"type": "string", "description": "Second object name."},
                    "chain": {"type": "string", "description": "Chain identifier (default 'A')."},
                    "divergence_threshold": {"type": "number", "description": "Distance threshold in angstroms (default 1.5)."}
                },
                "required": ["object1", "object2"]
            },
            return_schema={"type": "object", "properties": {"divergent_residues_count": {"type": "integer"}, "max_displacement": {"type": "number"}}},
            preconditions=["two_or_more_objects"],
            postconditions=[],
            classification="read_only",
            risk_level="Tier A (read-only)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_compare_residues
        ))

        self.register(Capability(
            id="align.identify_mutations",
            name="identify_mutations",
            api_mapping="sequence align + coords",
            category="08 Structure alignment",
            description="Compare wildtype and mutant structures, calculating global alignment and local Cα displacements at mutation sites.",
            parameters={
                "type": "object",
                "properties": {
                    "wildtype_object": {"type": "string", "description": "Name of wildtype object."},
                    "mutant_object": {"type": "string", "description": "Name of mutant object."},
                    "chain": {"type": "string", "description": "Chain identifier (default 'A')."}
                },
                "required": ["wildtype_object", "mutant_object"]
            },
            return_schema={"type": "object", "properties": {"global_rmsd": {"type": "number"}, "mutations": {"type": "array"}}},
            preconditions=["two_or_more_objects"],
            postconditions=[],
            classification="read_only",
            risk_level="Tier A (read-only)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_identify_mutations
        ))

        # --------------------------------------------------------------------
        # 10 Editing and mutations
        # --------------------------------------------------------------------
        self.register(Capability(
            id="mutation.analyze_mutation",
            name="analyze_mutation",
            api_mapping="structure_inspector + contacts",
            category="10 Editing and mutations",
            description="Verify residue at sequence position (e.g. 'R132H' or 'resi 132'), inspect local neighborhood, and find polar contacts.",
            parameters={
                "type": "object",
                "properties": {
                    "mutation_notation": {"type": "string", "description": "Mutation string (e.g. 'R132H', 'Arg132His', 'resi 132')."},
                    "object_name": {"type": "string", "description": "Optional object name."},
                    "chain": {"type": "string", "description": "Chain identifier (default 'A')."},
                    "cutoff": {"type": "number", "description": "Neighborhood radius in angstroms (default 5.0)."}
                },
                "required": ["mutation_notation"]
            },
            return_schema={"type": "object", "properties": {"wildtype_match": {"type": "boolean"}, "residue_neighborhood_count": {"type": "integer"}}},
            preconditions=["objects_exist"],
            postconditions=[],
            classification="read_only",
            risk_level="Tier A (read-only)",
            requires_confirmation=False,
            status="implemented/tested",
            func=tools.tool_analyze_mutation
        ))


GLOBAL_CAPABILITY_REGISTRY = CapabilityRegistry()


def define_capability(
    id: Optional[str] = None,
    name: str = "",
    api_mapping: str = "",
    category: str = "",
    description: str = "",
    parameters: Optional[Dict[str, Any]] = None,
    return_schema: Optional[Dict[str, Any]] = None,
    func: Optional[Callable[..., Dict[str, Any]]] = None,
    preconditions: Optional[List[str]] = None,
    postconditions: Optional[List[str]] = None,
    classification: str = "read_only",
    risk_level: str = "Tier A (read-only)",
    requires_confirmation: bool = False,
    supported_pymol_version: str = ">=2.5, confirmed 3.1.0",
    registry: Optional[CapabilityRegistry] = None,
    cap_id: Optional[str] = None
) -> Capability:
    """
    Standardized capability expansion framework for registering new verified PyMOL tools.
    Validates parameter schema, API mapping, risk policy, and executable callable.
    Refuses auto-authorization of Tier X or unvetted raw PyMOL APIs.
    """
    eff_id = cap_id or id or ""
    if not eff_id or "." not in eff_id:
        raise ValueError(f"Capability ID must follow 'domain.name' convention: '{eff_id}'")
    if not name or not name.isidentifier():
        raise ValueError(f"Capability name must be a valid Python identifier: '{name}'")
    if not api_mapping:
        raise ValueError("Capability must specify underlying PyMOL api_mapping (e.g. 'cmd.fetch')")
    if not callable(func):
        raise TypeError(f"Capability '{name}' must provide an executable Python callable")
    if not isinstance(parameters, dict) or parameters.get("type") != "object":
        raise ValueError("Parameters must be a JSON Schema dict with type='object'")
    if "Tier X" in risk_level or risk_level.startswith("blocked") or "prohibited" in risk_level.lower():
        raise ValueError(f"Tier X / blocked capabilities cannot be authorized for model execution: '{name}'")

    cap = Capability(
        id=eff_id,
        name=name,
        api_mapping=api_mapping,
        category=category,
        description=description,
        parameters=parameters or {"type": "object", "properties": {}},
        return_schema=return_schema or {"type": "object", "properties": {}},
        preconditions=preconditions or [],
        postconditions=postconditions or [],
        classification=classification,
        risk_level=risk_level,
        requires_confirmation=requires_confirmation,
        runtime_available=True,
        supported_pymol_version=supported_pymol_version,
        status="implemented/tested",
        func=func
    )

    reg = registry or GLOBAL_CAPABILITY_REGISTRY
    reg.register(cap)
    return cap

