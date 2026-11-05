"""
Inspection of loaded PyMOL structures, chains, residues, ligands, and selections.
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from .executor import PyMOLExecutor


class StructureInspector:
    """
    Extracts structural information, residue sequences, ligands, and metadata from PyMOL.
    """

    def __init__(self, executor: Optional[PyMOLExecutor] = None):
        self.executor = executor or PyMOLExecutor()

    @property
    def cmd(self):
        return self.executor.cmd

    def get_loaded_objects(self) -> List[str]:
        """Return list of loaded molecular object names."""
        def _exec():
            return self.cmd.get_names("objects")
        return self.executor.run_safe(_exec)

    def get_object_info(self, object_name: str) -> Dict[str, Any]:
        """Return detailed structural statistics for a given object."""
        def _exec():
            if object_name not in self.cmd.get_names("all"):
                raise ValueError(f"Object or selection '{object_name}' does not exist.")

            total_atoms = self.cmd.count_atoms(object_name)
            protein_atoms = self.cmd.count_atoms(f"({object_name}) and polymer.protein")
            nucleic_atoms = self.cmd.count_atoms(f"({object_name}) and polymer.nucleic")
            ligand_atoms = self.cmd.count_atoms(f"({object_name}) and organic")
            solvent_atoms = self.cmd.count_atoms(f"({object_name}) and solvent")
            ion_atoms = self.cmd.count_atoms(f"({object_name}) and inorganic")

            chains = self.cmd.get_chains(object_name)

            # Get ligands
            ligand_res = []
            if ligand_atoms > 0:
                stored_ligands = set()
                self.cmd.iterate(f"({object_name}) and organic", "stored_ligands.add((resn, resi, chain))", space={"stored_ligands": stored_ligands})
                ligand_res = [{"resn": r[0], "resi": r[1], "chain": r[2]} for r in sorted(stored_ligands)]

            # Bounding box
            extent = self.cmd.get_extent(object_name)
            min_pt, max_pt = extent[0], extent[1]
            box_dims = [round(max_pt[i] - min_pt[i], 2) for i in range(3)]

            return {
                "name": object_name,
                "total_atoms": total_atoms,
                "protein_atoms": protein_atoms,
                "nucleic_atoms": nucleic_atoms,
                "ligand_atoms": ligand_atoms,
                "solvent_atoms": solvent_atoms,
                "ion_atoms": ion_atoms,
                "chains": chains,
                "ligands": ligand_res,
                "bounding_box_angstroms": box_dims,
                "min_coords": [round(x, 2) for x in min_pt],
                "max_coords": [round(x, 2) for x in max_pt]
            }

        return self.executor.run_safe(_exec)

    def get_chains(self, object_name: Optional[str] = None) -> Dict[str, List[str]]:
        """Return a mapping of objects to their chains."""
        def _exec():
            objs = [object_name] if object_name else self.cmd.get_names("objects")
            result = {}
            for obj in objs:
                result[obj] = self.cmd.get_chains(obj)
            return result

        return self.executor.run_safe(_exec)

    def get_residues(self, object_name: Optional[str] = None, chain: Optional[str] = None, polymer_only: bool = True) -> List[Dict[str, str]]:
        """
        Extract unique residues (resn, resi, chain) from an object/chain.
        """
        def _exec():
            sel_parts = []
            if object_name:
                sel_parts.append(f"model {object_name}")
            if chain:
                sel_parts.append(f"chain {chain}")
            if polymer_only:
                sel_parts.append("polymer")

            selection = " and ".join(sel_parts) if sel_parts else "all"

            stored_res = []
            seen = set()

            def collector(resn, resi, ch):
                key = (ch, resi, resn)
                if key not in seen:
                    seen.add(key)
                    stored_res.append({"chain": ch, "resi": str(resi), "resn": resn})

            self.cmd.iterate(selection, "collector(resn, resi, chain)", space={"collector": collector})
            return stored_res

        return self.executor.run_safe(_exec)

    def get_selection_info(self, selection: str) -> Dict[str, Any]:
        """Return information about an arbitrary selection."""
        def _exec():
            atom_count = self.cmd.count_atoms(selection)
            if atom_count == 0:
                return {
                    "selection": selection,
                    "atom_count": 0,
                    "residues": [],
                    "chains": []
                }

            stored_chains = set()
            stored_res = set()
            self.cmd.iterate(selection, "stored_chains.add(chain); stored_res.add((chain, resi, resn))", space={"stored_chains": stored_chains, "stored_res": stored_res})

            return {
                "selection": selection,
                "atom_count": atom_count,
                "chains": sorted(list(stored_chains)),
                "residue_count": len(stored_res),
                "residues": [{"chain": r[0], "resi": r[1], "resn": r[2]} for r in sorted(stored_res)]
            }

        return self.executor.run_safe(_exec)

    def count_atoms(self, selection: str = "all") -> int:
        """Count atoms in a selection."""
        def _exec():
            return int(self.cmd.count_atoms(selection))
        return self.executor.run_safe(_exec)

    def get_structure_summary(self) -> Dict[str, Any]:
        """
        Produce a high-level summary of all structures currently in PyMOL.
        Suitable for feeding into LLM context window.
        """
        def _exec():
            objects = self.cmd.get_names("objects")
            selections = self.cmd.get_names("selections")

            obj_summaries = []
            for obj in objects:
                info = self.get_object_info(obj)
                obj_summaries.append(info)

            return {
                "object_count": len(objects),
                "objects": obj_summaries,
                "named_selections": selections
            }

        return self.executor.run_safe(_exec)

    def get_context_for_prompt(self) -> str:
        """Format a concise text summary of current state for the LLM system prompt."""
        try:
            summary = self.get_structure_summary()
            if summary["object_count"] == 0:
                return "PyMOL Context: No molecular objects are currently loaded in the PyMOL session."

            lines = [f"PyMOL Context: {summary['object_count']} object(s) loaded:"]
            for obj in summary["objects"]:
                chains_str = ", ".join(obj["chains"]) if obj["chains"] else "none"
                ligands_str = ""
                if obj["ligands"]:
                    ligands_str = "; Ligands: " + ", ".join([f"{l['resn']} ({l['resi']}:{l['chain']})" for l in obj["ligands"][:5]])
                lines.append(f"  • '{obj['name']}': {obj['total_atoms']} atoms, Chains: [{chains_str}]{ligands_str}")

            if summary["named_selections"]:
                lines.append("  Active selections: " + ", ".join(summary["named_selections"]))

            return "\n".join(lines)
        except Exception as e:
            return f"PyMOL Context: Unable to inspect session ({e})"

