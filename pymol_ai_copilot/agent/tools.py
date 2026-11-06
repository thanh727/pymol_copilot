"""
Concrete tool implementations for PyMOL structure inspection, manipulation, analysis, and export.
"""

import csv
import json
import os
import tempfile
from typing import Any, Dict, List, Optional

from ..analysis.alignment import StructureAligner
from ..analysis.contacts import ContactAnalyzer
from ..analysis.mutation import MutationAnalyzer
from ..analysis.ligand import LigandAnalyzer
from ..analysis.sasa import SASAAnalyzer
from ..analysis.epitope import EpitopeMapper
from ..analysis.batch import BatchStructureAnalyzer
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
        self.ligand = LigandAnalyzer(self.executor)
        self.sasa = SASAAnalyzer(self.executor)
        self.epitope = EpitopeMapper(self.executor)
        self.batch = BatchStructureAnalyzer(self.executor)


GLOBAL_CONTEXT = ToolContext()


# ============================================================================
# Export path sandbox
# ============================================================================

def _allowed_export_roots() -> List[str]:
    """Return the real paths exports are permitted to be written under."""
    candidates = [CONFIG.export_dir, tempfile.gettempdir()]
    candidates.extend(getattr(CONFIG, "additional_export_dirs", []) or [])
    roots: List[str] = []
    for candidate in candidates:
        if not candidate:
            continue
        try:
            root = os.path.realpath(os.path.expanduser(str(candidate)))
        except (OSError, ValueError):
            continue
        if root not in roots:
            roots.append(root)
    return roots


def _is_within(path: str, root: str) -> bool:
    try:
        return os.path.commonpath([path, root]) == root
    except ValueError:
        return False


def _resolve_export_path(filename: str, suffix: str = "") -> str:
    """Resolve an export path and refuse writes outside the allowed roots.

    Relative paths are anchored to ``CONFIG.export_dir``. Symlinks are resolved
    before the containment check so a link cannot escape the sandbox.
    """
    if not isinstance(filename, str) or not filename.strip():
        raise ValueError("An export path is required.")

    raw = os.path.expanduser(filename.strip())
    path = raw if os.path.isabs(raw) else os.path.join(CONFIG.export_dir, raw)
    if suffix and not path.lower().endswith(suffix.lower()):
        path += suffix

    if os.path.exists(path) or os.path.islink(path):
        resolved = os.path.realpath(path)
    else:
        parent = os.path.realpath(os.path.dirname(os.path.abspath(path)))
        resolved = os.path.join(parent, os.path.basename(path))

    roots = _allowed_export_roots()
    if not any(_is_within(resolved, root) for root in roots):
        raise PermissionError(
            "Refusing to write outside the allowed export directories. "
            f"Requested: '{resolved}'. Allowed roots: {roots}. "
            "Set 'export_dir' or 'additional_export_dirs' in the Copilot "
            "configuration to authorize another location."
        )
    return resolved


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


def tool_highlight_residues(selection: str = "", residues: Optional[Any] = None, representation: str = "sticks", color: str = "yellow") -> Dict[str, Any]:
    """Highlight residues using a specific representation and distinct color."""
    try:
        if not selection and residues:
            if isinstance(residues, list):
                parts = []
                for item in residues:
                    if isinstance(item, dict):
                        ch = item.get("chain", "")
                        ri = item.get("resi") or item.get("residue_number", "")
                        if ch and ri:
                            parts.append(f"(chain '{ch}' and resi '{ri}')")
                        elif ri:
                            parts.append(f"resi '{ri}'")
                    elif isinstance(item, str):
                        parts.append(f"resi '{item}'")
                selection = " or ".join(parts) if parts else "all"
            elif isinstance(residues, str):
                selection = residues
        if not selection:
            selection = "all"
        selection = GLOBAL_CONTEXT.executor.normalize_selection(selection)
        GLOBAL_CONTEXT.executor.show_representation(representation, selection)
        GLOBAL_CONTEXT.executor.color_selection(color, selection)
        return {"success": True, "highlighted": selection, "representation": representation, "color": color}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_label_residues(selection: str = "", label_type: str = "resn_resi", label: Optional[str] = None, residues: Optional[Any] = None, **kwargs) -> Dict[str, Any]:
    """Label residues with a fixed, allow-listed label style."""
    allowed_types = {"resn_resi", "resi", "clear"}
    effective_type = label if label is not None else label_type
    if not isinstance(effective_type, str) or effective_type not in allowed_types:
        return {
            "success": False,
            "error": (
                f"Unsupported label_type {effective_type!r}. "
                f"Allowed values: {sorted(allowed_types)}."
            )
        }
    try:
        if not selection and residues:
            if isinstance(residues, list):
                parts = []
                for item in residues:
                    if isinstance(item, dict):
                        ch = item.get("chain", "")
                        ri = item.get("resi") or item.get("residue_number", "")
                        if ch and ri:
                            parts.append(f"(chain '{ch}' and resi '{ri}')")
                        elif ri:
                            parts.append(f"resi '{ri}'")
                    elif isinstance(item, str):
                        parts.append(f"resi '{item}'")
                selection = " or ".join(parts) if parts else "all"
            elif isinstance(residues, str):
                selection = residues
        if not selection:
            selection = kwargs.get("target") or kwargs.get("target_selection") or "all"
        selection = GLOBAL_CONTEXT.executor.normalize_selection(selection)

        def _exec():
            GLOBAL_CONTEXT.executor.validate_selection(selection)
            if effective_type == "resn_resi":
                GLOBAL_CONTEXT.executor.cmd.label(selection, '"%s%s" % (resn, resi)')
            elif effective_type == "resi":
                GLOBAL_CONTEXT.executor.cmd.label(selection, "resi")
            elif effective_type == "clear":
                GLOBAL_CONTEXT.executor.cmd.label(selection, '""')
            else:
                raise ValueError(f"Unsupported label_type: {effective_type!r}")

        GLOBAL_CONTEXT.executor.run_safe(_exec)
        return {"success": True, "labeled_selection": selection, "label_type": effective_type}
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
    cycles: int = 5,
    mobile_chain: str = "",
    target_chain: str = "",
    **kwargs
) -> Dict[str, Any]:
    """Align mobile object onto target reference and calculate RMSD."""
    try:
        res = GLOBAL_CONTEXT.aligner.align_structures(
            mobile, target, mobile_selection, target_selection, method, cutoff, cycles, mobile_chain, target_chain
        )
        res["success"] = True
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_calculate_rmsd(
    mobile_selection: str,
    target_selection: str,
    atom_type: str = "CA",
    align_first: bool = False,
    mobile_chain: str = "",
    target_chain: str = "",
    **kwargs
) -> Dict[str, Any]:
    """Calculate RMSD between two selections with explicit atom filtering (CA, backbone, or all)."""
    try:
        res = GLOBAL_CONTEXT.aligner.calculate_rmsd(
            mobile_selection, target_selection, atom_type, align_first, mobile_chain, target_chain
        )
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
        res = GLOBAL_CONTEXT.mutations.compare_wildtype_and_mutant(
            wildtype_object=wildtype_object,
            mutant_object=mutant_object,
            mutation_str=resi or "",
            chain=chain
        )
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
        path = _resolve_export_path(filename, suffix=".png")
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
        path = _resolve_export_path(filename)
        saved = GLOBAL_CONTEXT.executor.save_session(path)
        return {"success": True, "filepath": saved}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_export_pml(filename: str) -> Dict[str, Any]:
    """Export all executed PyMOL commands as a reproducible .pml script."""
    try:
        path = _resolve_export_path(filename, suffix=".pml")
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
        path = _resolve_export_path(filename, suffix=".json")
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return {"success": True, "filepath": path}
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_export_analysis_csv(filename: str, rows: List[Dict[str, Any]], headers: Optional[List[str]] = None) -> Dict[str, Any]:
    """Export tabular analysis results to a CSV file."""
    try:
        path = _resolve_export_path(filename, suffix=".csv")
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


# ============================================================================
# F. Phase 4: Advanced Structural Biology Tools
# ============================================================================

# --- Ligand Interaction Analysis Tools ---

def tool_identify_ligands(object_name: str) -> Dict[str, Any]:
    """Identify bound ligands in a structure, distinguishing them from additives and solvent."""
    try:
        res = GLOBAL_CONTEXT.ligand.identify_ligands(object_name)
        res["success"] = True
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_analyze_ligand_interactions(
    object_name: str,
    ligand_resn: str = "",
    ligand_resi: str = "",
    ligand_chain: str = "",
    cutoff: float = 4.0,
    altloc: str = "A"
) -> Dict[str, Any]:
    """Analyze contacting residues, minimum heavy-atom distances, and polar contacts for a ligand."""
    try:
        res = GLOBAL_CONTEXT.ligand.analyze_ligand_interactions(
            object_name=object_name,
            ligand_resn=ligand_resn,
            ligand_resi=ligand_resi,
            ligand_chain=ligand_chain,
            cutoff=float(cutoff),
            altloc=altloc
        )
        res["success"] = True
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_visualize_ligand_pocket(
    object_name: str,
    ligand_resn: str,
    ligand_resi: str = "",
    ligand_chain: str = "",
    cutoff: float = 4.0,
    show_contacts: bool = True
) -> Dict[str, Any]:
    """Render publication-grade visualization of ligand binding pocket with dashes for polar contacts."""
    try:
        res = GLOBAL_CONTEXT.ligand.visualize_ligand_pocket(
            object_name=object_name,
            ligand_resn=ligand_resn,
            ligand_resi=ligand_resi,
            ligand_chain=ligand_chain,
            cutoff=float(cutoff),
            show_contacts=bool(show_contacts)
        )
        res["success"] = True
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_export_ligand_contacts(
    object_name: str,
    output_path: str,
    ligand_resn: str = "",
    ligand_resi: str = "",
    cutoff: float = 4.0,
    format: str = "json"
) -> Dict[str, Any]:
    """Export ligand contact table to a JSON or CSV file."""
    try:
        analysis = GLOBAL_CONTEXT.ligand.analyze_ligand_interactions(
            object_name=object_name,
            ligand_resn=ligand_resn,
            ligand_resi=ligand_resi,
            cutoff=float(cutoff)
        )
        path = _resolve_export_path(
            output_path,
            suffix=".csv" if str(format).lower().strip() == "csv" else ".json"
        )
        res = GLOBAL_CONTEXT.ligand.export_contacts_table(analysis, path, format)
        res["success"] = True
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- Solvent Accessibility (SASA) Tools ---

def tool_calculate_sasa(
    object_name: str,
    selection: str = "",
    probe_radius: float = 1.4,
    dot_density: int = 2
) -> Dict[str, Any]:
    """Calculate absolute SASA (Å²) and relative solvent accessibility (RSA %) per residue."""
    try:
        res = GLOBAL_CONTEXT.sasa.calculate_sasa(
            object_name=object_name,
            selection=selection,
            probe_radius=float(probe_radius),
            dot_density=int(dot_density)
        )
        res["success"] = True
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_map_sasa_to_structure(
    object_name: str,
    selection: str = "",
    probe_radius: float = 1.4,
    palette: str = "blue_white_red",
    representation: str = "surface"
) -> Dict[str, Any]:
    """Load atomic SASA into B-factors and color the molecular surface or cartoon by accessibility."""
    try:
        res = GLOBAL_CONTEXT.sasa.map_sasa_to_structure(
            object_name=object_name,
            selection=selection,
            probe_radius=float(probe_radius),
            palette=palette,
            representation=representation
        )
        res["success"] = True
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_compare_sasa(
    object1: str,
    object2: str,
    chain1: str = "A",
    chain2: str = "A",
    probe_radius: float = 1.4
) -> Dict[str, Any]:
    """Compare residue SASA between two structures (e.g. apo vs holo, or wild-type vs mutant)."""
    try:
        res = GLOBAL_CONTEXT.sasa.compare_sasa(
            object1=object1,
            object2=object2,
            chain1=chain1,
            chain2=chain2,
            probe_radius=float(probe_radius)
        )
        res["success"] = True
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_export_sasa_table(
    object_name: str,
    output_path: str,
    selection: str = "",
    probe_radius: float = 1.4,
    format: str = "json"
) -> Dict[str, Any]:
    """Calculate and export residue SASA / RSA table to a JSON or CSV file."""
    try:
        sasa_data = GLOBAL_CONTEXT.sasa.calculate_sasa(object_name, selection, probe_radius)
        path = _resolve_export_path(
            output_path,
            suffix=".csv" if str(format).lower().strip() == "csv" else ".json"
        )
        res = GLOBAL_CONTEXT.sasa.export_sasa_table(sasa_data, path, format)
        res["success"] = True
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- Epitope Structural Mapping Tools ---

def tool_map_epitope_sequence(
    object_name: str,
    epitope_sequence: str = "",
    residue_list: str = "",
    chain: str = ""
) -> Dict[str, Any]:
    """Map a linear epitope sequence or residue range to 3D structure, checking accessibility and clustering."""
    try:
        res = GLOBAL_CONTEXT.epitope.map_epitope_sequence(
            object_name=object_name,
            epitope_sequence=epitope_sequence,
            residue_list=residue_list,
            chain=chain
        )
        res["success"] = True
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


def tool_visualize_epitope(
    object_name: str,
    chain: str,
    residue_numbers: Any,
    representation: str = "surface_highlight"
) -> Dict[str, Any]:
    """Visualize mapped epitope locus with contrasting highlights on the protein surface or spheres."""
    try:
        if isinstance(residue_numbers, str):
            res_list = [r.strip() for r in residue_numbers.replace(",", " ").split() if r.strip()]
        else:
            res_list = [str(r) for r in residue_numbers]

        res = GLOBAL_CONTEXT.epitope.visualize_epitope(
            object_name=object_name,
            chain=chain,
            residue_numbers=res_list,
            representation=representation
        )
        res["success"] = True
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- WT-Mutant Structural Comparison Tool ---

def tool_compare_wt_mutant(
    wildtype_object: str,
    mutant_object: str,
    mutation_str: str = "",
    chain: str = "A",
    radius: float = 5.0
) -> Dict[str, Any]:
    """Compare wild-type and mutant structures: alignment, local C-alpha displacement, contact network deltas."""
    try:
        res = GLOBAL_CONTEXT.mutations.compare_wildtype_and_mutant(
            wildtype_object=wildtype_object,
            mutant_object=mutant_object,
            mutation_str=mutation_str,
            chain=chain,
            radius=float(radius)
        )
        res["success"] = True
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- Batch Structural Analysis Tool ---

def tool_batch_compare_structures(
    structure_names: Any,
    reference_name: str = "",
    chain: str = "A",
    method: str = "align",
    output_dir: str = ""
) -> Dict[str, Any]:
    """Perform pairwise structural alignment across a batch of structures against a common reference."""
    try:
        if isinstance(structure_names, str):
            names = [s.strip() for s in structure_names.replace(",", " ").split() if s.strip()]
        else:
            names = list(structure_names)

        out_d = _resolve_export_path(output_dir) if output_dir else ""
        res = GLOBAL_CONTEXT.batch.batch_compare_structures(
            structure_names=names,
            reference_name=reference_name,
            chain=chain,
            method=method,
            output_dir=out_d
        )
        if res.get("results"):
            res["success"] = True
            if res.get("failed_structures"):
                res["warning"] = (
                    f"{len(res['failed_structures'])} of {res.get('total_structures_analyzed', 0)} "
                    "structures could not be compared; see 'failed_structures' for details."
                )
        else:
            errors = "; ".join(
                f"{item.get('structure')}: {item.get('error')}"
                for item in res.get("failed_structures", [])
            )
            res["success"] = False
            res["error"] = (
                "Batch comparison produced no successful alignments."
                + (f" Failures: {errors}" if errors else "")
            )
        return res
    except Exception as e:
        return {"success": False, "error": str(e)}


