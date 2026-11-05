"""
Concrete tool implementations for PyMOL structure inspection, manipulation, analysis, and export.
"""

import csv
import json
import os
from typing import Any, Dict, List, Optional, Union

from ..analysis.alignment import StructureAligner
from ..analysis.contacts import ContactAnalyzer
from ..analysis.mutation import MutationAnalyzer
from ..config import CONFIG
from ..pymol_bridge.executor import PyMOLExecutor
from ..pymol_bridge.structure_inspector import StructureInspector
from ..pymol_bridge.visualization import VisualizationPresetManager


class ToolContext:
    """Shared context for tool executions."""
    def __init__(self):
        self.executor = PyMOLExecutor()
        self.inspector = StructureInspector(self.executor)
        self.vis_manager = VisualizationPresetManager(self.executor)
        self.aligner = StructureAligner(self.executor)
        self.contacts = ContactAnalyzer(self.executor)
        self.mutations = MutationAnalyzer(self.executor)


GLOBAL_CONTEXT = ToolContext()


# ============================================================================
# Structure Loading Tools
# ============================================================================

def tool_fetch_structure(pdb_id: str, object_name: Optional[str] = None, format: str = "cif") -> Dict[str, Any]:
    """Download and load a structure from the Protein Data Bank (PDB)."""
    try:
        res = GLOBAL_CONTEXT.executor.fetch_structure(pdb_id, object_name, format)
        res["success"] = True
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_load_structure(file_path: str, object_name: Optional[str] = None) -> Dict[str, Any]:
    """Load a molecular structure from a local file (e.g. .pdb, .cif, .mol2)."""
    try:
        res = GLOBAL_CONTEXT.executor.load_structure(file_path, object_name)
        res["success"] = True
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# A. Structure Inspection Tools
# ============================================================================

def tool_list_objects(object_type: str = "all") -> Dict[str, Any]:
    """List loaded molecular objects and selections in PyMOL."""
    try:
        objs = GLOBAL_CONTEXT.inspector.get_loaded_objects()
        selections = GLOBAL_CONTEXT.executor.list_objects("selections")
        return {
            "success": True,
            "object_count": len(objs),
            "objects": objs,
            "named_selections": selections
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_get_object_info(object_name: str) -> Dict[str, Any]:
    """Get atom counts, chains, ligands, and bounding box dimensions for an object."""
    try:
        info = GLOBAL_CONTEXT.inspector.get_object_info(object_name)
        info["success"] = True
        return info
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_get_chains(object_name: Optional[str] = None) -> Dict[str, Any]:
    """Get all chains present in loaded objects."""
    try:
        chains = GLOBAL_CONTEXT.inspector.get_chains(object_name)
        return {"success": True, "chains": chains}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_get_residues(object_name: Optional[str] = None, chain: Optional[str] = None, polymer_only: bool = True) -> Dict[str, Any]:
    """Get list of residues (chain, resi, resn) for an object and chain."""
    try:
        residues = GLOBAL_CONTEXT.inspector.get_residues(object_name, chain, polymer_only)
        return {
            "success": True,
            "count": len(residues),
            "residues": residues[:100],  # Truncate if extremely large to prevent context overflow
            "truncated": len(residues) > 100
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_get_selection_info(selection: str) -> Dict[str, Any]:
    """Get atom and residue count and chains for any selection expression."""
    try:
        info = GLOBAL_CONTEXT.inspector.get_selection_info(selection)
        info["success"] = True
        return info
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_count_atoms(selection: str = "all") -> Dict[str, Any]:
    """Count number of atoms matching a selection."""
    try:
        count = GLOBAL_CONTEXT.inspector.count_atoms(selection)
        return {"success": True, "selection": selection, "atom_count": count}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_get_structure_summary() -> Dict[str, Any]:
    """Get comprehensive summary of all structures, chains, ligands, and active selections."""
    try:
        summary = GLOBAL_CONTEXT.inspector.get_structure_summary()
        summary["success"] = True
        return summary
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# B. Molecular Visualization Tools
# ============================================================================

def tool_show_representation(representation: str, selection: str = "all") -> Dict[str, Any]:
    """Show molecular representation (cartoon, sticks, spheres, surface, ribbon, lines, etc.)."""
    try:
        res = GLOBAL_CONTEXT.executor.show_representation(representation, selection)
        return {"success": True, **res}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_hide_representation(representation: str = "everything", selection: str = "all") -> Dict[str, Any]:
    """Hide representation (e.g. everything, lines, cartoon, sticks)."""
    try:
        res = GLOBAL_CONTEXT.executor.hide_representation(representation, selection)
        return {"success": True, **res}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_color_selection(color: str, selection: str = "all") -> Dict[str, Any]:
    """Color selection (e.g. 'bychain', 'byelement', 'red', 'marine', 'yellow', 'rainbow')."""
    try:
        res = GLOBAL_CONTEXT.executor.color_selection(color, selection)
        return {"success": True, **res}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_select_residues(selection_name: str, selection_expr: str) -> Dict[str, Any]:
    """Create a named selection in PyMOL using standard selection algebra."""
    try:
        count = GLOBAL_CONTEXT.executor.select(selection_name, selection_expr)
        return {"success": True, "name": selection_name, "selection": selection_expr, "atom_count": count}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_highlight_residues(selection: str, representation: str = "sticks", color: str = "yellow") -> Dict[str, Any]:
    """Highlight residues using a specific representation and distinct color."""
    try:
        GLOBAL_CONTEXT.executor.show_representation(representation, selection)
        GLOBAL_CONTEXT.executor.color_selection(color, selection)
        return {"success": True, "highlighted": selection, "representation": representation, "color": color}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_label_residues(selection: str, label_type: str = "resn_resi") -> Dict[str, Any]:
    """Label residues with identifier text (resn_resi, resi, or custom)."""
    try:
        def _exec():
            if label_type == "resn_resi":
                GLOBAL_CONTEXT.executor.cmd.label(selection, '"%s%s" % (resn, resi)')
            elif label_type == "resi":
                GLOBAL_CONTEXT.executor.cmd.label(selection, "resi")
            elif label_type == "clear":
                GLOBAL_CONTEXT.executor.cmd.label(selection, '""')
            else:
                GLOBAL_CONTEXT.executor.cmd.label(selection, f'"{label_type}"')

        GLOBAL_CONTEXT.executor.run_safe(_exec)
        return {"success": True, "labeled_selection": selection, "label_type": label_type}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_set_transparency(transparency: float, selection: str = "all", representation: str = "surface") -> Dict[str, Any]:
    """Set transparency between 0.0 (opaque) and 1.0 (fully transparent)."""
    try:
        GLOBAL_CONTEXT.executor.set_transparency(transparency, selection, representation)
        return {"success": True, "transparency": transparency, "selection": selection, "representation": representation}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_orient_selection(selection: str = "all") -> Dict[str, Any]:
    """Orient camera along principal axes of selection."""
    try:
        GLOBAL_CONTEXT.executor.orient(selection)
        return {"success": True, "oriented": selection}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_zoom_selection(selection: str = "all", buffer: float = 2.0) -> Dict[str, Any]:
    """Zoom camera in on selection with buffer in angstroms."""
    try:
        GLOBAL_CONTEXT.executor.zoom(selection, buffer)
        return {"success": True, "zoomed": selection, "buffer_angstroms": buffer}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_set_background(color: str = "white") -> Dict[str, Any]:
    """Set background color of the PyMOL viewer (e.g. 'white', 'black', 'grey80')."""
    try:
        GLOBAL_CONTEXT.executor.set_background(color)
        return {"success": True, "background_color": color}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_reset_view() -> Dict[str, Any]:
    """Reset the 3D camera to default orientation."""
    try:
        GLOBAL_CONTEXT.executor.reset_view()
        return {"success": True, "view_reset": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_apply_visualization_preset(preset_name: str, target_selection: str = "all", **kwargs) -> Dict[str, Any]:
    """
    Apply a publication-ready visualization preset:
    - 'cartoon_by_chain'
    - 'binding_pocket' (requires ligand_selection)
    - 'mutation_neighborhood' (requires mutation_selection)
    - 'epitope' (requires epitope_selection)
    """
    try:
        p = preset_name.lower().strip()
        if p == "cartoon_by_chain":
            bg = kwargs.get("bg_color", "white")
            res = GLOBAL_CONTEXT.vis_manager.preset_cartoon_by_chain(target_selection, bg)
        elif p == "binding_pocket":
            lig = kwargs.get("ligand_selection", target_selection)
            cutoff = float(kwargs.get("cutoff", 5.0))
            prot = kwargs.get("protein_object")
            res = GLOBAL_CONTEXT.vis_manager.preset_binding_pocket(lig, cutoff, prot)
        elif p == "mutation_neighborhood":
            mut = kwargs.get("mutation_selection", target_selection)
            rad = float(kwargs.get("radius", 5.0))
            col = kwargs.get("color", "firebrick")
            res = GLOBAL_CONTEXT.vis_manager.preset_mutation_neighborhood(mut, rad, col)
        elif p == "epitope":
            epi = kwargs.get("epitope_selection", target_selection)
            col = kwargs.get("color", "magenta")
            res = GLOBAL_CONTEXT.vis_manager.preset_epitope(epi, col)
        else:
            raise ValueError(f"Unknown preset: '{preset_name}'. Options: cartoon_by_chain, binding_pocket, mutation_neighborhood, epitope")

        res["success"] = True
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# C. Structure Comparison Tools
# ============================================================================

def tool_align_structures(
    mobile: str,
    target: str,
    mobile_selection: str = "",
    target_selection: str = "",
    method: str = "align",
    cutoff: float = 2.0,
    cycles: int = 5
) -> Dict[str, Any]:
    """Align mobile object onto target reference and calculate RMSD."""
    try:
        res = GLOBAL_CONTEXT.aligner.align_structures(
            mobile, target, mobile_selection, target_selection, method, cutoff, cycles
        )
        res["success"] = True
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_calculate_rmsd(
    mobile_selection: str,
    target_selection: str,
    atom_type: str = "CA",
    align_first: bool = False
) -> Dict[str, Any]:
    """Calculate RMSD between two selections with explicit atom filtering (CA, backbone, or all)."""
    try:
        res = GLOBAL_CONTEXT.aligner.calculate_rmsd(mobile_selection, target_selection, atom_type, align_first)
        res["success"] = True
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_compare_residues(
    structure1: str,
    structure2: str,
    chain1: str = "A",
    chain2: str = "A",
    deviation_threshold: float = 2.0
) -> Dict[str, Any]:
    """Identify residues with high Cα distance deviation (> threshold Å) between two aligned structures."""
    try:
        res = GLOBAL_CONTEXT.aligner.compare_residues(structure1, structure2, chain1, chain2, deviation_threshold)
        res["success"] = True
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_identify_mutations(
    wildtype_object: str,
    mutant_object: str,
    chain: str = "A",
    resi: Optional[str] = None
) -> Dict[str, Any]:
    """Compare wildtype and mutant structures, calculating global alignment and local Cα displacement."""
    try:
        res = GLOBAL_CONTEXT.mutations.compare_wildtype_and_mutant(wildtype_object, mutant_object, chain, resi)
        res["success"] = True
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# D. Molecular Interaction Tools
# ============================================================================

def tool_calculate_distances(
    selection1: str,
    selection2: str,
    cutoff: float = 5.0,
    name: str = "ai_dist"
) -> Dict[str, Any]:
    """Calculate pairwise distances between atoms in selection1 and selection2 within cutoff."""
    try:
        res = GLOBAL_CONTEXT.contacts.calculate_distances(selection1, selection2, cutoff, name)
        res["success"] = True
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_find_nearby_residues(
    target_selection: str,
    cutoff: float = 5.0,
    surrounding_scope: str = "polymer"
) -> Dict[str, Any]:
    """Identify residues surrounding a target within cutoff angstroms."""
    try:
        res = GLOBAL_CONTEXT.contacts.find_nearby_residues(target_selection, cutoff, surrounding_scope)
        res["success"] = True
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_find_polar_contact_candidates(
    selection1: str,
    selection2: str,
    cutoff: float = 3.5,
    name: str = "ai_polar_contacts"
) -> Dict[str, Any]:
    """Find geometric polar contact candidates (N/O donor/acceptor pairs <= cutoff Å)."""
    try:
        res = GLOBAL_CONTEXT.contacts.find_polar_contact_candidates(selection1, selection2, cutoff, name)
        res["success"] = True
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_inspect_binding_pocket(
    ligand_selection: str,
    cutoff: float = 5.0,
    protein_object: Optional[str] = None
) -> Dict[str, Any]:
    """Inspect binding pocket around a ligand, classifying hydrophobic, polar, and aromatic residues."""
    try:
        res = GLOBAL_CONTEXT.contacts.inspect_binding_pocket(ligand_selection, cutoff, protein_object)
        res["success"] = True
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_analyze_mutation(
    mutation_str: str,
    object_name: Optional[str] = None,
    chain: Optional[str] = None,
    radius: float = 5.0
) -> Dict[str, Any]:
    """Verify residue at sequence position, analyze local contacts, and highlight mutation neighborhood."""
    try:
        res = GLOBAL_CONTEXT.mutations.verify_and_analyze_mutation(mutation_str, object_name, chain, radius)
        # Apply visualization
        mut_sel = f"model {res['object']} and chain {res['chain']} and resi {res['resi']}"
        GLOBAL_CONTEXT.vis_manager.preset_mutation_neighborhood(mut_sel, radius)
        res["success"] = True
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============================================================================
# E. Output and Reporting Tools
# ============================================================================

def tool_export_png(
    filename: str,
    width: int = 1920,
    height: int = 1080,
    dpi: int = 300,
    ray: int = 1
) -> Dict[str, Any]:
    """Export a high-resolution PNG image of the current view."""
    try:
        path = filename if os.path.isabs(filename) else os.path.join(CONFIG.export_dir, filename)
        if not path.lower().endswith(".png"):
            path += ".png"
        saved = GLOBAL_CONTEXT.executor.export_image(path, width, height, dpi, ray)
        return {
            "success": True,
            "filepath": saved,
            "resolution": f"{width}x{height}",
            "dpi": dpi,
            "ray_traced": bool(ray)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_save_session(filename: str) -> Dict[str, Any]:
    """Save the current PyMOL session to a .pse file."""
    try:
        path = filename if os.path.isabs(filename) else os.path.join(CONFIG.export_dir, filename)
        saved = GLOBAL_CONTEXT.executor.save_session(path)
        return {"success": True, "filepath": saved}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_export_pml(filename: str) -> Dict[str, Any]:
    """Export all executed PyMOL commands as a reproducible .pml script."""
    try:
        path = filename if os.path.isabs(filename) else os.path.join(CONFIG.export_dir, filename)
        if not path.lower().endswith(".pml"):
            path += ".pml"
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        script = GLOBAL_CONTEXT.executor.get_pml_script()
        with open(path, "w", encoding="utf-8") as f:
            f.write(script)
        return {"success": True, "filepath": path, "command_count": len(GLOBAL_CONTEXT.executor.get_history())}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_export_analysis_json(filename: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Export structural analysis results to a JSON file."""
    try:
        path = filename if os.path.isabs(filename) else os.path.join(CONFIG.export_dir, filename)
        if not path.lower().endswith(".json"):
            path += ".json"
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return {"success": True, "filepath": path}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_export_analysis_csv(filename: str, rows: List[Dict[str, Any]], headers: Optional[List[str]] = None) -> Dict[str, Any]:
    """Export tabular analysis results to a CSV file."""
    try:
        path = filename if os.path.isabs(filename) else os.path.join(CONFIG.export_dir, filename)
        if not path.lower().endswith(".csv"):
            path += ".csv"
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        if not rows:
            return {"success": False, "error": "No rows provided for CSV export."}

        fieldnames = headers or list(rows[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows:
                writer.writerow({k: r.get(k, "") for k in fieldnames})
        return {"success": True, "filepath": path, "row_count": len(rows)}
    except Exception as e:
        return {"success": False, "error": str(e)}

