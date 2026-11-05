#!/usr/bin/env python3
"""Non-destructive inventory of the installed PyMOL command-language and Python API.

Usage (with the Python interpreter that imports the installed PyMOL):
    python pymol_api_inventory.py --output-dir ./pymol_inventory

Outputs:
    pymol_api_inventory.json
    pymol_api_inventory.csv
    pymol_api_inventory.md

No PyMOL commands are executed except the optional read-only get_version() call.
This inventories callable public attributes of pymol.cmd and its PML command
registry; it does NOT cover all Python internals or third-party plugins.
"""
from __future__ import annotations

import argparse
import csv
import inspect
import json
import platform
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Curated command vocabulary from the PyMOL command reference, PyMOL Wiki,
# and the open-source cmd/keywords registry. Runtime availability is checked.
CATEGORIES = {
    "01 Input, retrieval, files": "fetch load save multifilesave multisave load_traj read_pdbstr read_molstr load_model load_cgo png mpng get_pdbstr get_cifstr get_session set_session",
    "02 Object and session management": "create copy extract group ungroup order delete remove disable enable set_name get_names get_names_of_type get_type get_object_list reinitialize count_states split_states join_states",
    "03 Structure inspection": "get_model get_chains count_atoms get_object_matrix get_coords get_coordset get_atom_coords get_extent identify index get_symmetry get_title get_version get_object_state get_selection_state get_position get_bonds get_distance get_angle get_dihedral get_view get_setting_tuple get_setting_int get_setting_float get_setting_text",
    "04 Selection and atom queries": "select deselect indicate mask unmask flag protect deprotect get_unused_name pop get_names get_model get_atom_coords",
    "05 Representation and color": "show show_as hide color color_deep set_color set_bond set_color spectrum set transparency util dss cartoon ribbon sphere_mode recolor label set_title",
    "06 Camera and viewport": "orient origin zoom center reset view get_view set_view rotate translate turn move clip rock viewport full_screen get_position matrix_copy matrix_reset",
    "07 Distances and geometry": "distance dist get_distance angle get_angle dihedral get_dihedral measure set_dihedral centerofmass get_extent",
    "08 Structure alignment": "align super cealign fit pair_fit rms rms_cur intra_fit intra_rms intra_rms_cur get_raw_alignment",
    "09 Surface and accessibility": "get_area get_sasa_relative set dot isosurface isomesh isodot get_surface_vertex",
    "10 Editing and mutations": "alter alter_state iterate iterate_state edit attach replace remove bond unbond fuse h_add h_fill sort create extract fab fragment pseudoatom smooth sculpt_activate sculpt_iterate sculpt_deactivate undo redo push_undo",
    "11 Maps and volumetric": "map_new map_set map_trim map_double map_set_border isomesh isosurface isodot isolevel load_volume volume volume_color volume_ramp_new ramp_new gradient slice_new",
    "12 States and trajectories": "load_traj count_states split_states join_states set_state frame count_frames smooth morph get_coordset set_coordset",
    "13 Movies and scenes": "mset mdo mview mplay mstop mclear mpng frame count_frames rewind forward backward middle ending scene",
    "14 Rendering and figures": "png ray draw capture viewport bg_color set_color set get view set_view stereo scene",
    "15 Settings and configuration": "get set unset unset_deep set_bond get_setting_tuple get_setting_int get_setting_float get_setting_text set_color button config_mouse mouse",
    "16 Crystallography and symmetry": "symexp set_symmetry get_symmetry map_new isosurface isomesh",
    "17 Command language and extension": "help commands extend extendaa alias run do python system cd ls pwd log_open log_close log_resume log_append quit reinitialize",
}
# Ordered, intentional priority classification for multi-category functions.
PRIORITY = [
    "01 Input, retrieval, files", "02 Object and session management",
    "03 Structure inspection", "04 Selection and atom queries",
    "05 Representation and color", "06 Camera and viewport",
    "07 Distances and geometry", "08 Structure alignment",
    "09 Surface and accessibility", "10 Editing and mutations",
    "11 Maps and volumetric", "12 States and trajectories",
    "13 Movies and scenes", "14 Rendering and figures",
    "15 Settings and configuration", "16 Crystallography and symmetry",
    "17 Command language and extension",
]
ASSOCIATIONS: dict[str, list[str]] = {}
for category in PRIORITY:
    for name in CATEGORIES[category].split():
        ASSOCIATIONS.setdefault(name, []).append(category)

# The categories describe RISK/APPROVAL requirements for an adapter, not
# proof that a callable is safe just because it appears in the inventory.
BLOCKED = {
    "system", "python", "run", "do", "extend", "extendaa", "alias",
    "quit", "cd", "log_open", "log_append", "log_resume", "log_close",
    "conda", "fork", "spawn", "exec", "eval", "reinitialize",
}
DESTRUCTIVE = {
    "delete", "remove", "extract", "alter", "alter_state", "replace",
    "bond", "unbond", "fuse", "attach", "remove_picked", "set_session",
    "set_coordset", "load_model", "load_cgo", "create", "smooth",
    "sculpt_iterate", "set_dihedral", "h_add", "h_fill", "rename",
}
WRITE_OR_NETWORK = {
    "save", "multisave", "multifilesave", "png", "mpng", "fetch",
    "load", "load_traj", "read_pdbstr", "read_molstr", "get_session",
}
READ_ONLY = {
    "get_model", "get_chains", "count_atoms", "get_names", "get_names_of_type",
    "get_type", "get_object_list", "get_coords", "get_atom_coords",
    "get_coordset", "get_extent", "get_distance", "get_angle",
    "get_dihedral", "get_area", "get_sasa_relative", "get_view",
    "get_setting_tuple", "get_setting_float", "get_setting_int",
    "get_setting_text", "get_version", "get_symmetry", "get_raw_alignment",
    "get_selection_state", "get_object_state", "identify", "index",
    "count_states", "count_frames", "get_position", "get_object_matrix",
    "get_title", "get_pdbstr", "get_cifstr", "get_bonds",
}
VIEW_ONLY = {
    "show", "show_as", "hide", "color", "color_deep", "spectrum",
    "set_color", "bg_color", "orient", "zoom", "center", "reset",
    "origin", "rotate", "turn", "move", "clip", "rock", "view",
    "set_view", "get_view", "label", "set_title", "recolor",
    "refresh", "rebuild", "dss", "viewport", "full_screen",
}

def classify(name: str) -> str:
    if name in BLOCKED:
        return "blocked: never directly expose to LLM"
    if name in DESTRUCTIVE:
        return "mutation: approval or dedicated guarded workflow"
    if name in WRITE_OR_NETWORK:
        return "I/O: allowlisted paths/network and collision checks"
    if name in READ_ONLY:
        return "read-only candidate: typed adapter required"
    if name in VIEW_ONLY:
        return "view candidate: bounded parameters and undo strategy"
    return "manual review: NOT auto-authorized"


def first_doc_line(obj: Any) -> str:
    try:
        docs = inspect.getdoc(obj) or ""
        for line in docs.splitlines():
            line = line.strip()
            if line and line.upper() not in {"DESCRIPTION", "USAGE", "EXAMPLES", "ARGUMENTS"}:
                return line[:240]
    except (TypeError, ValueError, Exception):
        pass
    return ""


def signature(obj: Any) -> str:
    try:
        return str(inspect.signature(obj))
    except (TypeError, ValueError, Exception):
        return "<unavailable>"


def inventory() -> dict[str, Any]:
    try:
        import pymol
        from pymol import cmd
    except ImportError as exc:
        raise SystemExit(
            "PyMOL is not importable in this Python environment. "
            "Use the Python executable associated with your installed PyMOL. "
            f"Original error: {exc}"
        ) from exc

    registry = getattr(cmd, "keyword", {})
    if not isinstance(registry, dict):
        registry = {}

    names = {n for n in dir(cmd) if not n.startswith("_")}
    # Note: PML keyword may be a command alias or not a same-named cmd attr.
    names.update(n for n in registry if isinstance(n, str) and not n.startswith("_"))
    entries = []
    for name in sorted(names, key=str.casefold):
        try:
            obj = getattr(cmd, name, None)
        except Exception:
            obj = None
        keyword_entry = registry.get(name)
        if not callable(obj) and keyword_entry is not None:
            try:
                obj = keyword_entry[0]
            except (IndexError, TypeError, KeyError):
                pass
        is_callable = callable(obj)
        if not is_callable and name not in registry:
            continue
        categories = ASSOCIATIONS.get(name, ["99 Uncategorized / review"])
        entries.append({
            "name": name,
            "in_python_api": callable(getattr(cmd, name, None)),
            "in_pml_registry": name in registry,
            "categories": categories,
            "primary_category": categories[0],
            "signature": signature(obj) if is_callable else "<PML keyword>",
            "module": getattr(obj, "__module__", "") if is_callable else "",
            "description": first_doc_line(obj) if is_callable else "",
            "risk_policy": classify(name),
            "availability": "observed in installed runtime",
            "llm_exposed": False,
        })

    version = "unknown"
    try:
        version = str(cmd.get_version()[0])
    except Exception:
        pass

    return {
        "metadata": {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "pymol_version": version,
            "python_version": sys.version.split()[0],
            "python_executable": sys.executable,
            "platform": platform.platform(),
            "api_functions_or_pml_keywords": len(entries),
            "in_pml_registry": sum(e["in_pml_registry"] for e in entries),
            "in_python_api": sum(e["in_python_api"] for e in entries),
            "scope": "public callable attributes of pymol.cmd plus PML command registry",
            "disclaimer": "Discovery only; not an authorization list or guarantees of capability correctness",
        },
        "entries": entries,
    }


def save_report(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "pymol_api_inventory.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    fields = [
        "name", "in_python_api", "in_pml_registry", "primary_category",
        "categories", "signature", "module", "description", "risk_policy",
        "availability", "llm_exposed",
    ]
    with (output_dir / "pymol_api_inventory.csv").open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        for e in report["entries"]:
            row = dict(e)
            row["categories"] = "; ".join(row["categories"])
            writer.writerow(row)

    metadata = report["metadata"]
    counts = Counter(e["primary_category"] for e in report["entries"])
    lines = [
        "# Installed PyMOL API inventory", "",
        f"- PyMOL: `{metadata['pymol_version']}`",
        f"- Python: `{metadata['python_version']}` (`{metadata['python_executable']}`)",
        f"- Public Python API / PML command entries: **{metadata['api_functions_or_pml_keywords']}**",
        f"- PML command registry names: **{metadata['in_pml_registry']}**",
        f"- Public callable cmd attributes: **{metadata['in_python_api']}**",
        "", "**Inventory is not a tool allowlist. All entries default to LLM-disallowed.**", "",
        "## Category overview", "", "| Category | Number of primary entries |", "|---|---:|",
    ]
    for category, count in sorted(counts.items()):
        lines.append(f"| {category} | {count} |")
    lines.extend(["", "## Discovered commands and Python API", ""])
    for category in sorted(counts):
        lines.append(f"### {category}")
        lines.append("")
        lines.append("| Name | API | PML | Risk | Signature |")
        lines.append("|---|:---:|:---:|---|---|")
        for e in report["entries"]:
            if e["primary_category"] != category:
                continue
            sig = e["signature"].replace("|", "\\|").replace("`", "'")
            lines.append(
                f"| `{e['name']}` | {'Yes' if e['in_python_api'] else 'No'} | "
                f"{'Yes' if e['in_pml_registry'] else 'No'} | "
                f"{e['risk_policy']} | `{sig}` |"
            )
        lines.append("")
    (output_dir / "pymol_api_inventory.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("./pymol_inventory"))
    args = parser.parse_args()
    report = inventory()
    save_report(report, args.output_dir.resolve())
    print(json.dumps(report["metadata"], indent=2))
    print(f"Inventory written to: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
