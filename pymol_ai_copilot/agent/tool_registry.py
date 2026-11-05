"""
Typed tool registry, JSON schemas for Ollama function calling, and execution dispatcher.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
from . import tools


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]
    func: Callable[..., Dict[str, Any]]

    def to_ollama_format(self) -> Dict[str, Any]:
        """Convert to Ollama / OpenAI function calling schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }


class ToolRegistry:
    """
    Central registry for all verified PyMOL AI Copilot tools.
    Enforces strict whitelist execution and argument validation.
    """

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._register_all_tools()

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        return list(self._tools.values())

    def get_ollama_tools(self, subset: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        if subset:
            subset_set = set(subset)
            return [t.to_ollama_format() for t in self._tools.values() if t.name in subset_set]
        return [t.to_ollama_format() for t in self._tools.values()]

    def execute(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute tool with whitelist validation.
        Never executes arbitrary code.
        """
        tool = self._tools.get(name)
        if not tool:
            return {
                "success": False,
                "error": f"Tool '{name}' is not in the authorized tool registry. Available tools: {list(self._tools.keys())}"
            }

        try:
            # Dispatch to verified tool function
            return tool.func(**arguments)
        except TypeError as e:
            return {
                "success": False,
                "error": f"Invalid arguments provided for tool '{name}': {e}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Tool execution failed for '{name}': {e}"
            }

    def _register_all_tools(self):
        # Structure Loading Tools
        self.register(ToolDefinition(
            name="fetch_structure",
            description="Download and load a molecular structure directly from the Protein Data Bank (PDB) into PyMOL. Use this when the user asks to download, fetch, or open a structure by its PDB ID (e.g. '1ubq', '1ake', '4hhb') or AlphaFold accession.",
            parameters={
                "type": "object",
                "properties": {
                    "pdb_id": {
                        "type": "string",
                        "description": "Standard 4-character PDB accession ID (e.g. '1ubq', '1ake') or AlphaFold accession code."
                    },
                    "object_name": {
                        "type": "string",
                        "description": "Optional custom name for the loaded object. If omitted, defaults to the lowercase PDB ID."
                    },
                    "format": {
                        "type": "string",
                        "description": "File format: 'cif' (default, modern mmCIF) or 'pdb'.",
                        "enum": ["cif", "pdb"]
                    }
                },
                "required": ["pdb_id"]
            },
            func=tools.tool_fetch_structure
        ))

        self.register(ToolDefinition(
            name="load_structure",
            description="Load a molecular structure from a local filesystem path (PDB, mmCIF, mol2, sdf) into PyMOL. Use this when the user specifies an existing local file.",
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Local file path to the molecular structure file."
                    },
                    "object_name": {
                        "type": "string",
                        "description": "Optional name for the loaded PyMOL object. If omitted, defaults to the filename without extension."
                    }
                },
                "required": ["file_path"]
            },
            func=tools.tool_load_structure
        ))

        # A. Structure Inspection
        self.register(ToolDefinition(
            name="list_objects",
            description="List all molecular objects and active selections currently loaded in PyMOL.",
            parameters={
                "type": "object",
                "properties": {
                    "object_type": {
                        "type": "string",
                        "description": "Type of objects to return: 'all' or 'selections'.",
                        "enum": ["all", "selections"]
                    }
                },
                "required": []
            },
            func=tools.tool_list_objects
        ))

        self.register(ToolDefinition(
            name="get_object_info",
            description="Get structural statistics for an object: atom counts (protein, nucleic, ligand, solvent, ions), chains, ligands, and bounding box dimensions.",
            parameters={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string", "description": "Name of the PyMOL object to inspect."}
                },
                "required": ["object_name"]
            },
            func=tools.tool_get_object_info
        ))

        self.register(ToolDefinition(
            name="get_chains",
            description="Get the list of chains for loaded objects.",
            parameters={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string", "description": "Optional object name to filter by."}
                },
                "required": []
            },
            func=tools.tool_get_chains
        ))

        self.register(ToolDefinition(
            name="get_residues",
            description="Get the sequence of residues (resn, resi, chain) in a protein or chain.",
            parameters={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string", "description": "Optional object name."},
                    "chain": {"type": "string", "description": "Optional chain identifier (e.g. 'A')."},
                    "polymer_only": {"type": "boolean", "description": "Only return polymer residues (ignore waters/ligands). Default true."}
                },
                "required": []
            },
            func=tools.tool_get_residues
        ))

        self.register(ToolDefinition(
            name="get_selection_info",
            description="Get atom count, residue count, and chains for any PyMOL selection expression.",
            parameters={
                "type": "object",
                "properties": {
                    "selection": {"type": "string", "description": "PyMOL selection expression (e.g. 'chain A and resi 1-50')."}
                },
                "required": ["selection"]
            },
            func=tools.tool_get_selection_info
        ))

        self.register(ToolDefinition(
            name="count_atoms",
            description="Count the total number of atoms matching a selection.",
            parameters={
                "type": "object",
                "properties": {
                    "selection": {"type": "string", "description": "PyMOL selection expression."}
                },
                "required": ["selection"]
            },
            func=tools.tool_count_atoms
        ))

        self.register(ToolDefinition(
            name="get_structure_summary",
            description="Get a complete overview of all loaded objects, chains, ligands, and active selections.",
            parameters={"type": "object", "properties": {}, "required": []},
            func=tools.tool_get_structure_summary
        ))

        # B. Molecular Visualization
        self.register(ToolDefinition(
            name="show_representation",
            description="Show a 3D molecular representation for a selection (e.g. cartoon, sticks, spheres, surface).",
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
            func=tools.tool_show_representation
        ))

        self.register(ToolDefinition(
            name="hide_representation",
            description="Hide a molecular representation (e.g. 'everything', 'cartoon', 'lines', 'sticks').",
            parameters={
                "type": "object",
                "properties": {
                    "representation": {"type": "string", "description": "Representation to hide (default 'everything')."},
                    "selection": {"type": "string", "description": "PyMOL selection expression (default 'all')."}
                },
                "required": []
            },
            func=tools.tool_hide_representation
        ))

        self.register(ToolDefinition(
            name="color_selection",
            description="Apply color to a selection. Supports color names ('marine', 'red', 'yellow'), 'bychain' (colors each chain differently), 'byelement' (element coloring with carbons matching), or 'rainbow'.",
            parameters={
                "type": "object",
                "properties": {
                    "color": {"type": "string", "description": "Color name, 'bychain', 'byelement', or 'rainbow'."},
                    "selection": {"type": "string", "description": "PyMOL selection expression (default 'all')."}
                },
                "required": ["color"]
            },
            func=tools.tool_color_selection
        ))

        self.register(ToolDefinition(
            name="select_residues",
            description="Create a named selection in PyMOL for future reference (e.g. name='ligand_pocket', selection='byres organic expand 5').",
            parameters={
                "type": "object",
                "properties": {
                    "selection_name": {"type": "string", "description": "Identifier name for the selection."},
                    "selection_expr": {"type": "string", "description": "PyMOL selection query string."}
                },
                "required": ["selection_name", "selection_expr"]
            },
            func=tools.tool_select_residues
        ))

        self.register(ToolDefinition(
            name="highlight_residues",
            description="Highlight specific residues with a chosen representation (e.g. 'sticks') and distinct color (e.g. 'yellow'). Accepts selection string or residues list.",
            parameters={
                "type": "object",
                "properties": {
                    "selection": {"type": "string", "description": "Residues to highlight (e.g. 'chain A and resi 8-15')."},
                    "residues": {"description": "List of residue dicts (e.g. from find_nearby_residues)."},
                    "representation": {"type": "string", "description": "Representation (default 'sticks')."},
                    "color": {"type": "string", "description": "Color name (default 'yellow')."}
                }
            },
            func=tools.tool_highlight_residues
        ))

        self.register(ToolDefinition(
            name="label_residues",
            description="Add 3D text labels to residues in PyMOL (e.g. 'resn_resi' for 'ARG132', 'resi' for '132', or 'clear' to remove).",
            parameters={
                "type": "object",
                "properties": {
                    "selection": {"type": "string", "description": "PyMOL selection to label."},
                    "label_type": {
                        "type": "string",
                        "description": "Label style: 'resn_resi', 'resi', or 'clear'.",
                        "enum": ["resn_resi", "resi", "clear"]
                    }
                },
                "required": ["selection"]
            },
            func=tools.tool_label_residues
        ))

        self.register(ToolDefinition(
            name="set_transparency",
            description="Set surface or cartoon transparency between 0.0 (opaque) and 1.0 (invisible).",
            parameters={
                "type": "object",
                "properties": {
                    "transparency": {"type": "number", "description": "Transparency value from 0.0 to 1.0."},
                    "selection": {"type": "string", "description": "Selection expression."},
                    "representation": {"type": "string", "description": "'surface' or 'cartoon'."}
                },
                "required": ["transparency"]
            },
            func=tools.tool_set_transparency
        ))

        self.register(ToolDefinition(
            name="orient_selection",
            description="Orient the camera along the principal axes of the given selection.",
            parameters={
                "type": "object",
                "properties": {
                    "selection": {"type": "string", "description": "Selection to orient (default 'all')."}
                },
                "required": []
            },
            func=tools.tool_orient_selection
        ))

        self.register(ToolDefinition(
            name="zoom_selection",
            description="Center and zoom the camera onto a selection.",
            parameters={
                "type": "object",
                "properties": {
                    "selection": {"type": "string", "description": "Selection to zoom in on (default 'all')."},
                    "buffer": {"type": "number", "description": "Margin buffer in angstroms (default 2.0)."}
                },
                "required": []
            },
            func=tools.tool_zoom_selection
        ))

        self.register(ToolDefinition(
            name="set_background",
            description="Set the background color of the PyMOL 3D viewport (e.g. 'white', 'black', 'grey80').",
            parameters={
                "type": "object",
                "properties": {
                    "color": {"type": "string", "description": "Background color name (e.g. 'white')."}
                },
                "required": ["color"]
            },
            func=tools.tool_set_background
        ))

        self.register(ToolDefinition(
            name="reset_view",
            description="Reset the 3D viewport camera to the initial default orientation.",
            parameters={"type": "object", "properties": {}, "required": []},
            func=tools.tool_reset_view
        ))

        self.register(ToolDefinition(
            name="apply_visualization_preset",
            description="Apply a coordinated publication preset: 'cartoon_by_chain', 'binding_pocket', 'mutation_neighborhood', or 'epitope'.",
            parameters={
                "type": "object",
                "properties": {
                    "preset_name": {
                        "type": "string",
                        "description": "Preset name: 'cartoon_by_chain', 'binding_pocket', 'mutation_neighborhood', 'epitope'.",
                        "enum": ["cartoon_by_chain", "binding_pocket", "mutation_neighborhood", "epitope"]
                    },
                    "target_selection": {"type": "string", "description": "Target selection or ligand/mutation/epitope selection."},
                    "cutoff": {"type": "number", "description": "Pocket or neighborhood radius in angstroms (default 5.0)."}
                },
                "required": ["preset_name"]
            },
            func=tools.tool_apply_visualization_preset
        ))

        # C. Structure Comparison
        self.register(ToolDefinition(
            name="align_structures",
            description="Superimpose mobile structure onto target reference and calculate RMSD. Methods: 'align' (sequence-informed), 'super' (structure-based), 'cealign' (combinatorial extension). Supports explicit chain scoping.",
            parameters={
                "type": "object",
                "properties": {
                    "mobile": {"type": "string", "description": "Name of object to move/align."},
                    "target": {"type": "string", "description": "Name of reference structure."},
                    "method": {
                        "type": "string",
                        "description": "Alignment algorithm: 'align', 'super', or 'cealign'.",
                        "enum": ["align", "super", "cealign"]
                    },
                    "cutoff": {"type": "number", "description": "Outlier rejection cutoff in angstroms (default 2.0)."},
                    "cycles": {"type": "integer", "description": "Max refinement cycles (default 5)."},
                    "mobile_chain": {"type": "string", "description": "Optional specific chain for mobile structure (e.g. 'A')."},
                    "target_chain": {"type": "string", "description": "Optional specific chain for target reference structure (e.g. 'A')."}
                },
                "required": ["mobile", "target"]
            },
            func=tools.tool_align_structures
        ))

        self.register(ToolDefinition(
            name="calculate_rmsd",
            description="Calculate RMSD between two selections with explicit atom filtering ('CA', 'backbone', or 'all') and optional chain filtering.",
            parameters={
                "type": "object",
                "properties": {
                    "mobile_selection": {"type": "string", "description": "Mobile selection."},
                    "target_selection": {"type": "string", "description": "Target selection."},
                    "atom_type": {"type": "string", "description": "Atom filter: 'CA', 'backbone', or 'all'.", "enum": ["CA", "backbone", "all"]},
                    "align_first": {"type": "boolean", "description": "Whether to superimpose before calculating RMSD (default false)."},
                    "mobile_chain": {"type": "string", "description": "Optional specific chain for mobile selection."},
                    "target_chain": {"type": "string", "description": "Optional specific chain for target selection."}
                },
                "required": ["mobile_selection", "target_selection"]
            },
            func=tools.tool_calculate_rmsd
        ))

        self.register(ToolDefinition(
            name="compare_residues",
            description="Identify residue positions with structural divergence (Cα distance > threshold Å) between two aligned structures.",
            parameters={
                "type": "object",
                "properties": {
                    "structure1": {"type": "string", "description": "First structure name."},
                    "structure2": {"type": "string", "description": "Second structure name."},
                    "chain1": {"type": "string", "description": "Chain in first structure (default 'A')."},
                    "chain2": {"type": "string", "description": "Chain in second structure (default 'A')."},
                    "deviation_threshold": {"type": "number", "description": "Distance cutoff in angstroms to flag deviation (default 2.0)."}
                },
                "required": ["structure1", "structure2"]
            },
            func=tools.tool_compare_residues
        ))

        self.register(ToolDefinition(
            name="identify_mutations",
            description="Compare wildtype and mutant structures, calculating global alignment and local Cα displacement at mutation site.",
            parameters={
                "type": "object",
                "properties": {
                    "wildtype_object": {"type": "string", "description": "Wild-type structure name."},
                    "mutant_object": {"type": "string", "description": "Mutant structure name."},
                    "chain": {"type": "string", "description": "Chain identifier (default 'A')."},
                    "resi": {"type": "string", "description": "Optional residue number to compare locally."}
                },
                "required": ["wildtype_object", "mutant_object"]
            },
            func=tools.tool_identify_mutations
        ))

        # D. Molecular Interactions
        self.register(ToolDefinition(
            name="calculate_distances",
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
            func=tools.tool_calculate_distances
        ))

        self.register(ToolDefinition(
            name="find_nearby_residues",
            description="Find all polymer residues within cutoff angstroms of a target selection (e.g. 'organic', 'resn AP5', 'resi 50').",
            parameters={
                "type": "object",
                "properties": {
                    "target_selection": {"type": "string", "description": "Target selection expression (e.g. 'organic', 'resn AP5', 'chain A and resi 100')."},
                    "cutoff": {"type": "number", "description": "Distance radius in angstroms (default 5.0)."},
                    "surrounding_scope": {"type": "string", "description": "Scope of surrounding search (default 'polymer')."}
                },
                "required": ["target_selection"]
            },
            func=tools.tool_find_nearby_residues
        ))

        self.register(ToolDefinition(
            name="find_polar_contact_candidates",
            description="Identify geometric polar contact candidates (potential hydrogen bond donor-acceptor atom pairs within <= 3.5 Å). Note: these are geometric candidates, not experimentally verified.",
            parameters={
                "type": "object",
                "properties": {
                    "selection1": {"type": "string", "description": "First selection."},
                    "selection2": {"type": "string", "description": "Second selection."},
                    "cutoff": {"type": "number", "description": "Maximum distance in angstroms (default 3.5)."}
                },
                "required": ["selection1", "selection2"]
            },
            func=tools.tool_find_polar_contact_candidates
        ))

        self.register(ToolDefinition(
            name="inspect_binding_pocket",
            description="Analyze a ligand binding pocket: identifies pocket residues, classifies hydrophobic, polar, and aromatic residues, and measures polar contact candidates.",
            parameters={
                "type": "object",
                "properties": {
                    "ligand_selection": {"type": "string", "description": "Selection for the ligand (e.g. 'organic' or 'resn STI')."},
                    "cutoff": {"type": "number", "description": "Pocket definition radius in angstroms (default 5.0)."},
                    "protein_object": {"type": "string", "description": "Optional protein object name."}
                },
                "required": ["ligand_selection"]
            },
            func=tools.tool_inspect_binding_pocket
        ))

        self.register(ToolDefinition(
            name="analyze_mutation",
            description="Verify residue at sequence position (e.g. 'R132H' or 'resi 132'), inspect local contact neighborhood within radius Å, and highlight in PyMOL.",
            parameters={
                "type": "object",
                "properties": {
                    "mutation_str": {"type": "string", "description": "Mutation string such as 'R132H', 'Arg132His', or residue number '132'."},
                    "object_name": {"type": "string", "description": "Optional object name."},
                    "chain": {"type": "string", "description": "Optional chain identifier (e.g. 'A')."},
                    "radius": {"type": "number", "description": "Neighborhood radius in angstroms (default 5.0)."}
                },
                "required": ["mutation_str"]
            },
            func=tools.tool_analyze_mutation
        ))

        # E. Output and Reporting
        self.register(ToolDefinition(
            name="export_png",
            description="Render and export a high-resolution PNG image of the current PyMOL 3D view.",
            parameters={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Output filename (e.g. 'pocket_figure.png')."},
                    "width": {"type": "integer", "description": "Image width in pixels (default 1920)."},
                    "height": {"type": "integer", "description": "Image height in pixels (default 1080)."},
                    "dpi": {"type": "integer", "description": "Image resolution DPI (default 300)."},
                    "ray": {"type": "integer", "description": "1 to enable ray tracing (default 1), 0 for fast OpenGL capture."}
                },
                "required": ["filename"]
            },
            func=tools.tool_export_png
        ))

        self.register(ToolDefinition(
            name="save_session",
            description="Save the entire PyMOL session state to a .pse file.",
            parameters={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Session file path (e.g. 'my_analysis.pse')."}
                },
                "required": ["filename"]
            },
            func=tools.tool_save_session
        ))

        self.register(ToolDefinition(
            name="export_pml",
            description="Export all executed PyMOL operations as a reproducible PyMOL command script (.pml).",
            parameters={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Output .pml filename."}
                },
                "required": ["filename"]
            },
            func=tools.tool_export_pml
        ))

        self.register(ToolDefinition(
            name="export_analysis_json",
            description="Save structured analysis data (RMSD, contacts, pocket residues) to a JSON file.",
            parameters={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Output JSON filename."},
                    "data": {"type": "object", "description": "Dictionary of analysis results to save."}
                },
                "required": ["filename", "data"]
            },
            func=tools.tool_export_analysis_json
        ))

        self.register(ToolDefinition(
            name="export_analysis_csv",
            description="Save tabular analysis rows (e.g. residue contacts or mutations) to a CSV file.",
            parameters={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Output CSV filename."},
                    "rows": {"type": "array", "description": "List of dictionary records.", "items": {"type": "object"}}
                },
                "required": ["filename", "rows"]
            },
            func=tools.tool_export_analysis_csv
        ))

        # --- Phase 4 Advanced Tools ---

        self.register(ToolDefinition(
            name="identify_ligands",
            description="Identify biologically relevant bound ligands in a loaded structure, distinguishing them from solvent, additives, and salts.",
            parameters={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string", "description": "Name of the PyMOL object to inspect."}
                },
                "required": ["object_name"]
            },
            func=tools.tool_identify_ligands
        ))

        self.register(ToolDefinition(
            name="analyze_ligand_interactions",
            description="Analyze protein contacting residues within a cutoff distance of a ligand, computing minimum heavy-atom distances and geometric polar contacts.",
            parameters={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string", "description": "Name of the PyMOL object."},
                    "ligand_resn": {"type": "string", "description": "3-letter residue name of the ligand (e.g. 'AP5')."},
                    "ligand_resi": {"type": "string", "description": "Residue sequence number of the ligand (e.g. '215')."},
                    "ligand_chain": {"type": "string", "description": "Chain identifier of the ligand (e.g. 'A')."},
                    "cutoff": {"type": "number", "description": "Distance cutoff in angstroms (default 4.0).", "default": 4.0},
                    "altloc": {"type": "string", "description": "Alternate conformation identifier to prioritize (default 'A').", "default": "A"}
                },
                "required": ["object_name"]
            },
            func=tools.tool_analyze_ligand_interactions
        ))

        self.register(ToolDefinition(
            name="visualize_ligand_pocket",
            description="Render publication-grade visualization of the ligand binding pocket with dashes for polar contacts and zoomed framing.",
            parameters={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string", "description": "Name of the PyMOL object."},
                    "ligand_resn": {"type": "string", "description": "3-letter residue name of the ligand."},
                    "ligand_resi": {"type": "string", "description": "Residue sequence number of the ligand."},
                    "ligand_chain": {"type": "string", "description": "Chain of the ligand."},
                    "cutoff": {"type": "number", "description": "Pocket radius in angstroms.", "default": 4.0},
                    "show_contacts": {"type": "boolean", "description": "Whether to draw dashed lines for polar contacts.", "default": True}
                },
                "required": ["object_name", "ligand_resn"]
            },
            func=tools.tool_visualize_ligand_pocket
        ))

        self.register(ToolDefinition(
            name="export_ligand_contacts",
            description="Export ligand contacting residues and minimum distances to a JSON or CSV file.",
            parameters={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string", "description": "Name of the PyMOL object."},
                    "output_path": {"type": "string", "description": "Output file path (JSON or CSV)."},
                    "ligand_resn": {"type": "string", "description": "Ligand residue name."},
                    "ligand_resi": {"type": "string", "description": "Ligand residue number."},
                    "cutoff": {"type": "number", "description": "Distance cutoff.", "default": 4.0},
                    "format": {"type": "string", "enum": ["json", "csv"], "default": "json"}
                },
                "required": ["object_name", "output_path"]
            },
            func=tools.tool_export_ligand_contacts
        ))

        self.register(ToolDefinition(
            name="calculate_sasa",
            description="Calculate total and per-residue solvent-accessible surface area (SASA, Å²) and relative solvent accessibility (RSA, %).",
            parameters={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string", "description": "Name of the PyMOL object."},
                    "selection": {"type": "string", "description": "Optional sub-selection (default all).", "default": ""},
                    "probe_radius": {"type": "number", "description": "Solvent probe sphere radius in angstroms.", "default": 1.4},
                    "dot_density": {"type": "integer", "description": "Dot surface density (1-4).", "default": 2}
                },
                "required": ["object_name"]
            },
            func=tools.tool_calculate_sasa
        ))

        self.register(ToolDefinition(
            name="map_sasa_to_structure",
            description="Map per-atom or per-residue SASA values into B-factors and color the molecular surface or cartoon by accessibility.",
            parameters={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string", "description": "Name of the PyMOL object."},
                    "selection": {"type": "string", "description": "Optional sub-selection.", "default": ""},
                    "probe_radius": {"type": "number", "description": "Solvent probe radius.", "default": 1.4},
                    "palette": {"type": "string", "description": "Color spectrum palette (e.g. 'blue_white_red').", "default": "blue_white_red"},
                    "representation": {"type": "string", "enum": ["surface", "cartoon"], "default": "surface"}
                },
                "required": ["object_name"]
            },
            func=tools.tool_map_sasa_to_structure
        ))

        self.register(ToolDefinition(
            name="compare_sasa",
            description="Compare residue SASA between two structures (e.g., apo vs holo, or wild-type vs mutant) to detect burying or exposure.",
            parameters={
                "type": "object",
                "properties": {
                    "object1": {"type": "string", "description": "First PyMOL object."},
                    "object2": {"type": "string", "description": "Second PyMOL object."},
                    "chain1": {"type": "string", "description": "Chain for first object.", "default": "A"},
                    "chain2": {"type": "string", "description": "Chain for second object.", "default": "A"},
                    "probe_radius": {"type": "number", "description": "Solvent probe radius in angstroms.", "default": 1.4}
                },
                "required": ["object1", "object2"]
            },
            func=tools.tool_compare_sasa
        ))

        self.register(ToolDefinition(
            name="export_sasa_table",
            description="Calculate and export residue SASA and relative accessibility (RSA) table to a JSON or CSV file.",
            parameters={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string", "description": "Name of the PyMOL object."},
                    "output_path": {"type": "string", "description": "Output file path (JSON or CSV)."},
                    "selection": {"type": "string", "description": "Optional sub-selection.", "default": ""},
                    "probe_radius": {"type": "number", "description": "Probe radius in angstroms.", "default": 1.4},
                    "format": {"type": "string", "enum": ["json", "csv"], "default": "json"}
                },
                "required": ["object_name", "output_path"]
            },
            func=tools.tool_export_sasa_table
        ))

        self.register(ToolDefinition(
            name="map_epitope_sequence",
            description="Map a linear epitope sequence or residue range to 3D structure, evaluating solvent accessibility and spatial clustering.",
            parameters={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string", "description": "Name of the PyMOL object."},
                    "epitope_sequence": {"type": "string", "description": "Linear peptide sequence (e.g. 'TITLEVE')."},
                    "residue_list": {"type": "string", "description": "Comma-separated residue numbers or range (e.g. '12-18' or '40,41,42')."},
                    "chain": {"type": "string", "description": "Optional chain identifier.", "default": ""}
                },
                "required": ["object_name"]
            },
            func=tools.tool_map_epitope_sequence
        ))

        self.register(ToolDefinition(
            name="visualize_epitope",
            description="Highlight mapped epitope residues on the protein structure using contrasting colors and surface or sphere representations.",
            parameters={
                "type": "object",
                "properties": {
                    "object_name": {"type": "string", "description": "Name of the PyMOL object."},
                    "chain": {"type": "string", "description": "Chain identifier containing the epitope."},
                    "residue_numbers": {"type": "array", "description": "List of residue numbers belonging to the epitope.", "items": {"type": "string"}},
                    "representation": {"type": "string", "enum": ["surface_highlight", "spheres"], "default": "surface_highlight"}
                },
                "required": ["object_name", "chain", "residue_numbers"]
            },
            func=tools.tool_visualize_epitope
        ))

        self.register(ToolDefinition(
            name="compare_wt_mutant",
            description="Perform sequence-aware alignment of WT and mutant structures, analyzing local C-alpha displacement and contact network changes.",
            parameters={
                "type": "object",
                "properties": {
                    "wildtype_object": {"type": "string", "description": "Name of wild-type PyMOL object."},
                    "mutant_object": {"type": "string", "description": "Name of mutant PyMOL object."},
                    "mutation_str": {"type": "string", "description": "Mutation notation (e.g. 'R42A' or 'Arg42Ala')."},
                    "chain": {"type": "string", "description": "Chain identifier (default 'A').", "default": "A"},
                    "radius": {"type": "number", "description": "Local neighborhood radius in angstroms.", "default": 5.0}
                },
                "required": ["wildtype_object", "mutant_object"]
            },
            func=tools.tool_compare_wt_mutant
        ))

        self.register(ToolDefinition(
            name="batch_compare_structures",
            description="Perform consistent pairwise structural alignment across a batch of structures against a common reference, exporting summary tables and overlay figures.",
            parameters={
                "type": "object",
                "properties": {
                    "structure_names": {"type": "array", "description": "List of loaded PyMOL object names.", "items": {"type": "string"}},
                    "reference_name": {"type": "string", "description": "Optional reference structure (default first structure in list)."},
                    "chain": {"type": "string", "description": "Chain to align (default 'A').", "default": "A"},
                    "method": {"type": "string", "enum": ["align", "super", "cealign"], "default": "align"},
                    "output_dir": {"type": "string", "description": "Optional directory to save comparison tables (CSV, JSON), overlay image, and session."}
                },
                "required": ["structure_names"]
            },
            func=tools.tool_batch_compare_structures
        ))


GLOBAL_REGISTRY = ToolRegistry()

