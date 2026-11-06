"""
Inspection of loaded PyMOL structures, chains, residues, ligands, and selections.
"""

from typing import Any, Dict, List, Optional
from .executor import PyMOLExecutor
from ..analysis.contacts import resi_sort_key


class StructureInspector:
    """
    Extracts structural information, residue sequences, ligands, and metadata from PyMOL.
    """

    def __init__(self, executor: Optional[PyMOLExecutor] = None):
        self.executor = executor or PyMOLExecutor()

    @property
    def cmd(self):
        return self.executor.cmd

    def _is_molecular_object(self, name: str) -> bool:
        """Return True only for molecular objects.

        ``get_names("objects")`` also returns measurement objects created by the
        PyMOL ``distance`` command. Those objects cannot be used in atom
        selections, so treating them as structures makes every later query fail
        with ``Invalid selection name``.
        """
        try:
            return self.cmd.get_type(name) == "object:molecule"
        except Exception:
            try:
                self.cmd.count_atoms(name)
                return True
            except Exception:
                return False

    def get_loaded_objects(self) -> List[str]:
        """Return list of loaded molecular object names."""
        def _exec():
            return [
                name for name in self.cmd.get_names("objects")
                if self._is_molecular_object(name)
            ]
        return self.executor.run_safe(_exec)

    def get_object_info(self, object_name: str) -> Dict[str, Any]:
        """Return detailed structural statistics for a given object."""
        def _exec():
            if object_name not in self.cmd.get_names("all"):
                raise ValueError(f"Object or selection '{object_name}' does not exist.")

            try:
                obj_type = self.cmd.get_type(object_name)
            except Exception:
                obj_type = ""
            if obj_type and obj_type != "object:molecule":
                raise ValueError(
                    f"'{object_name}' is not a molecular object "
                    f"(PyMOL type: {obj_type})."
                )

            total_atoms = self.cmd.count_atoms(object_name)
            protein_atoms = self.cmd.count_atoms(f"({object_name}) and polymer.protein")
            nucleic_atoms = self.cmd.count_atoms(f"({object_name}) and polymer.nucleic")
            ligand_atoms = self.cmd.count_atoms(f"({object_name}) and organic")
            solvent_atoms = self.cmd.count_atoms(f"({object_name}) and solvent")
            ion_atoms = self.cmd.count_atoms(f"({object_name}) and inorganic")

            chains = self.cmd.get_chains(object_name)

            # Get ligands (organic)
            ligand_res = []
            if ligand_atoms > 0:
                stored_ligands = set()
                self.cmd.iterate(f"({object_name}) and organic", "stored_ligands.add((resn, resi, chain))", space={"stored_ligands": stored_ligands})
                ligand_res = [{"resn": r[0], "resi": r[1], "chain": r[2]} for r in sorted(stored_ligands)]

            # Get all non-polymer, non-solvent heteroatoms including inorganic ions
            hetero_res = []
            if total_atoms > 0:
                stored_hetero = set()
                self.cmd.iterate(
                    f"({object_name}) and not polymer and not solvent",
                    "stored_hetero.add((resn, resi, chain))",
                    space={"stored_hetero": stored_hetero}
                )
                hetero_res = [{"resn": r[0], "resi": r[1], "chain": r[2]} for r in sorted(stored_hetero)]

            # Bounding box
            if total_atoms > 0:
                extent = self.cmd.get_extent(object_name)
                min_pt, max_pt = extent[0], extent[1]
                box_dims = [round(max_pt[i] - min_pt[i], 2) for i in range(3)]
                min_c = [round(x, 2) for x in min_pt]
                max_c = [round(x, 2) for x in max_pt]
            else:
                box_dims = [0.0, 0.0, 0.0]
                min_c = [0.0, 0.0, 0.0]
                max_c = [0.0, 0.0, 0.0]

            return {
                "name": object_name,
                "total_atoms": total_atoms,
                "protein_atoms": protein_atoms,
                "nucleic_atoms": nucleic_atoms,
                "ligand_atoms": ligand_atoms,
                "solvent_atoms": solvent_atoms,
                "ion_atoms": ion_atoms,
                "chains": chains,
                "ligands": sorted(ligand_res, key=lambda x: (x["chain"], resi_sort_key(x["resi"]))),
                "heteroatoms": sorted(hetero_res, key=lambda x: (x["chain"], resi_sort_key(x["resi"]))),
                "bounding_box_angstroms": box_dims,
                "min_coords": min_c,
                "max_coords": max_c
            }

        return self.executor.run_safe(_exec)

    def get_chains(self, object_name: Optional[str] = None) -> Dict[str, List[str]]:
        """Return a mapping of objects to their chains."""
        def _exec():
            if object_name:
                objs = [object_name]
            else:
                objs = [
                    name for name in self.cmd.get_names("objects")
                    if self._is_molecular_object(name)
                ]
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
        selection = self.executor.normalize_selection(selection)

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
                "residues": sorted(
                    [{"chain": r[0], "resi": str(r[1]), "resn": r[2]} for r in stored_res],
                    key=lambda x: (x["chain"], resi_sort_key(x["resi"]))
                )
            }

        return self.executor.run_safe(_exec)

    def count_atoms(self, selection: str = "all") -> int:
        """Count atoms in a selection."""
        selection = self.executor.normalize_selection(selection)

        def _exec():
            return int(self.cmd.count_atoms(selection))
        return self.executor.run_safe(_exec)

    def get_structure_summary(self) -> Dict[str, Any]:
        """
        Produce a high-level summary of all structures currently in PyMOL.
        Suitable for feeding into LLM context window.
        """
        def _exec():
            objects = [
                name for name in self.cmd.get_names("objects")
                if self._is_molecular_object(name)
            ]
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
                    ligands_str = "; Ligands: " + ", ".join([f"{lig['resn']} ({lig['resi']}:{lig['chain']})" for lig in obj["ligands"][:5]])
                hetero = obj.get("heteroatoms") or []
                hetero_str = ""
                if hetero:
                    hetero_str = "; Heteroatoms/ions: " + ", ".join(
                        f"{h['resn']} ({h['resi']}:{h['chain']})" for h in hetero[:10]
                    )
                lines.append(
                    f"  • '{obj['name']}': {obj['total_atoms']} atoms, Chains: [{chains_str}]"
                    f"{ligands_str}{hetero_str}"
                )

            if summary["named_selections"]:
                lines.append("  Active selections: " + ", ".join(summary["named_selections"]))

            return "\n".join(lines)
        except Exception as e:
            return f"PyMOL Context: Unable to inspect session ({e})"

