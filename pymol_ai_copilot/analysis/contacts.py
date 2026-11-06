"""
Intermolecular and intramolecular contact analysis, distances, and binding pockets.
"""

import re
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from ..pymol_bridge.executor import PyMOLExecutor


def resi_sort_key(resi_val: Any) -> Tuple[int, str]:
    """
    Safely sort residue numbers with optional insertion codes (e.g. '100', '100A', '-1').
    Returns (integer_part, insertion_code) to prevent comparison crashes in Python 3.
    """
    s = str(resi_val).strip()
    m = re.match(r"^([-+]?\d+)(.*)$", s)
    if m:
        try:
            return (int(m.group(1)), m.group(2))
        except ValueError:
            pass
    return (999999, s)


class ContactAnalyzer:
    """
    Performs distance measurements, contact residue identification, and binding pocket analysis.
    """

    POLAR_ATOMS = {"N", "O"}
    HYDROPHOBIC_RESIDUES = {"ALA", "VAL", "LEU", "ILE", "MET", "PHE", "TRP", "PRO"}
    CHARGED_POSITIVE = {"ARG", "LYS", "HIS"}
    CHARGED_NEGATIVE = {"ASP", "GLU"}
    AROMATIC_RESIDUES = {"PHE", "TYR", "TRP", "HIS"}

    def __init__(self, executor: Optional[PyMOLExecutor] = None):
        self.executor = executor or PyMOLExecutor()

    @property
    def cmd(self):
        return self.executor.cmd

    def _get_atoms_with_coords(self, selection: str) -> Tuple[List[Tuple[str, int]], np.ndarray]:
        """
        Extract unique atom identifiers (model, index) and their 3D coordinates (N, 3).
        """
        atom_info = []
        self.cmd.iterate_state(
            1, selection,
            "atom_info.append(((model, index), float(x), float(y), float(z)))",
            space={"atom_info": atom_info}
        )
        if not atom_info:
            return [], np.empty((0, 3), dtype=float)

        ids = [item[0] for item in atom_info]
        coords = np.array([[item[1], item[2], item[3]] for item in atom_info], dtype=float)
        return ids, coords

    def calculate_distances(
        self,
        selection1: str,
        selection2: str,
        cutoff: float = 5.0,
        name: str = "ai_dist"
    ) -> Dict[str, Any]:
        """
        Measure pairwise atomic distances between two selections within cutoff.
        Correctly excludes self-contacts (d = 0.0) and avoids duplicate pair counting when selections overlap.
        """
        selection1 = self.executor.normalize_selection(selection1)
        selection2 = self.executor.normalize_selection(selection2)

        def _exec():
            c1 = self.cmd.count_atoms(selection1)
            c2 = self.cmd.count_atoms(selection2)
            if c1 == 0 or c2 == 0:
                raise ValueError(f"One or both selections contain 0 atoms ({selection1}: {c1}, {selection2}: {c2}).")

            self.cmd.delete(name)
            # cmd.distance creates visual measurement dashes in PyMOL
            dist_val = self.cmd.distance(name, selection1, selection2, cutoff=float(cutoff), mode=0)

            ids1, coords1 = self._get_atoms_with_coords(selection1)
            ids2, coords2 = self._get_atoms_with_coords(selection2)

            pairs_within_cutoff = []
            if len(coords1) > 0 and len(coords2) > 0:
                diff = coords1[:, np.newaxis, :] - coords2[np.newaxis, :, :]
                dist_matrix = np.sqrt(np.sum(diff**2, axis=-1))

                # Check if identical sets (e.g. internal contacts)
                if ids1 == ids2:
                    # Upper triangle only, strictly above diagonal (k=1)
                    mask = (dist_matrix <= cutoff) & np.triu(np.ones_like(dist_matrix, dtype=bool), k=1)
                    within = dist_matrix[mask]
                else:
                    common_ids = set(ids1) & set(ids2)
                    if common_ids:
                        mask = dist_matrix <= cutoff
                        for i, id1 in enumerate(ids1):
                            for j, id2 in enumerate(ids2):
                                if id1 == id2:
                                    mask[i, j] = False
                                elif id1 in common_ids and id2 in common_ids and id1 > id2:
                                    mask[i, j] = False
                        within = dist_matrix[mask]
                    else:
                        within = dist_matrix[dist_matrix <= cutoff]

                pairs_within_cutoff = [round(float(d), 2) for d in np.sort(within)]

            pair_count = len(pairs_within_cutoff)
            if pair_count == 0 and dist_val > 0 and dist_val <= cutoff:
                pairs_within_cutoff = [round(float(dist_val), 2)]
                pair_count = 1

            min_dist = pairs_within_cutoff[0] if pairs_within_cutoff else None
            mean_dist = round(float(np.mean(pairs_within_cutoff)), 2) if pairs_within_cutoff else min_dist

            return {
                "success": True,
                "distance_object": name,
                "selection1": selection1,
                "selection2": selection2,
                "cutoff_angstroms": cutoff,
                "contact_pairs_count": pair_count,
                "minimum_distance_angstroms": min_dist,
                "average_distance_angstroms": mean_dist,
                "distances_sample": pairs_within_cutoff[:10]
            }

        res = self.executor.run_safe(_exec)
        self.executor.record_command(f"distance {name}, {selection1}, {selection2}, cutoff={cutoff}", "calculate_distances", {"selection1": selection1, "selection2": selection2, "cutoff": cutoff}, res)
        return res

    def find_nearby_residues(
        self,
        target_selection: str,
        cutoff: float = 5.0,
        surrounding_scope: str = "polymer"
    ) -> Dict[str, Any]:
        """
        Identify polymer residues within cutoff angstroms of target selection.
        Supports natural keywords like 'ligand' / 'ligands' / 'organic' and auto-resolves generic 'resn lig'.
        """
        target_selection = self.executor.normalize_selection(target_selection)

        def _exec():
            norm_target = target_selection.strip()
            # Support common ligand aliases
            if norm_target.lower() in ("ligand", "ligands"):
                norm_target = "organic and not solvent"
            elif norm_target.lower().startswith("resn lig") and self.cmd.count_atoms(norm_target) == 0:
                # If resn LIG was attempted but doesn't exist, check if organic ligands exist
                if self.cmd.count_atoms("organic and not solvent") > 0:
                    norm_target = "organic and not solvent"

            t_count = self.cmd.count_atoms(norm_target)
            if t_count == 0:
                stored_hetero = set()
                self.cmd.iterate(
                    "not polymer and not solvent",
                    "stored_hetero.add(resn)",
                    space={"stored_hetero": stored_hetero}
                )
                stored_solvent = set()
                self.cmd.iterate("solvent", "stored_solvent.add(resn)", space={"stored_solvent": stored_solvent})

                hints = []
                if stored_hetero:
                    hints.append(
                        f"Available non-solvent heteroatoms/ions: {sorted(stored_hetero)}. "
                        "Use 'resn <NAME>' with one of these names."
                    )
                if stored_solvent:
                    hints.append(f"Available solvent residues: {sorted(stored_solvent)}.")
                hint = (" " + " ".join(hints)) if hints else ""
                raise ValueError(
                    f"Target selection '{target_selection}' has 0 atoms.{hint}"
                )

            def _residues_near(selection: str) -> Dict[str, Any]:
                query = f"byres (({surrounding_scope}) within {cutoff} of ({selection})) and not ({selection})"
                atom_count = self.cmd.count_atoms(query)
                stored = set()
                self.cmd.iterate(query, "stored.add((chain, resi, resn))", space={"stored": stored})
                res_list = sorted(
                    [{"chain": r[0], "resi": str(r[1]), "resn": r[2]} for r in stored],
                    key=lambda x: (x["chain"], resi_sort_key(x["resi"]))
                )
                return {
                    "total_atoms": atom_count,
                    "residue_count": len(res_list),
                    "residues": res_list
                }

            combined = _residues_near(norm_target)

            # Break the result down per target residue instance. This matters
            # when a selection such as "resn SO4" matches several independent
            # ions/ligands: each one usually contacts a different residue set.
            target_stored = set()
            self.cmd.iterate(
                norm_target,
                "target_stored.add((chain, resi, resn))",
                space={"target_stored": target_stored}
            )
            target_list = sorted(
                [{"chain": r[0], "resi": str(r[1]), "resn": r[2]} for r in target_stored],
                key=lambda x: (x["chain"], resi_sort_key(x["resi"]))
            )

            per_instance = []
            for target in target_list[:50]:
                parts = [f"resn '{target['resn']}'", f"resi '{target['resi']}'"]
                if target["chain"]:
                    parts.append(f"chain '{target['chain']}'")
                instance_selection = " and ".join(parts)
                near = _residues_near(instance_selection)
                per_instance.append({
                    "target": target,
                    "selection": instance_selection,
                    "total_atoms": near["total_atoms"],
                    "residue_count": near["residue_count"],
                    "residues": near["residues"]
                })

            return {
                "success": True,
                "target_selection": norm_target,
                "requested_target": target_selection,
                "cutoff_angstroms": cutoff,
                "surrounding_scope": surrounding_scope,
                "target_count": len(target_list),
                "targets": target_list,
                "total_atoms": combined["total_atoms"],
                "residue_count": combined["residue_count"],
                "residues": combined["residues"],
                "per_instance": per_instance
            }

        return self.executor.run_safe(_exec)

    def find_polar_contact_candidates(
        self,
        selection1: str,
        selection2: str,
        cutoff: float = 3.5,
        name: str = "ai_polar_contacts"
    ) -> Dict[str, Any]:
        """
        Identify geometric polar contact candidates (N/O donor/acceptor pairs within cutoff).
        NOTE: These are distance-based geometric candidates, not experimentally verified hydrogen bonds.
        """
        selection1 = self.executor.normalize_selection(selection1)
        selection2 = self.executor.normalize_selection(selection2)

        def _exec():
            c1 = self.cmd.count_atoms(selection1)
            c2 = self.cmd.count_atoms(selection2)
            if c1 == 0 or c2 == 0:
                raise ValueError(f"Selection has 0 atoms ({selection1}: {c1}, {selection2}: {c2}).")

            self.cmd.delete(name)
            dist_val = self.cmd.distance(name, selection1, selection2, cutoff=float(cutoff), mode=2)

            # Polar atoms filter
            polar1_sel = f"({selection1}) and (elem N,O)"
            polar2_sel = f"({selection2}) and (elem N,O)"

            ids1, coords1 = self._get_atoms_with_coords(polar1_sel)
            ids2, coords2 = self._get_atoms_with_coords(polar2_sel)

            polar_dists = []
            if len(coords1) > 0 and len(coords2) > 0:
                diff = coords1[:, np.newaxis, :] - coords2[np.newaxis, :, :]
                mat = np.sqrt(np.sum(diff**2, axis=-1))

                if ids1 == ids2:
                    mask = (mat <= cutoff) & np.triu(np.ones_like(mat, dtype=bool), k=1)
                    within = mat[mask]
                else:
                    common_ids = set(ids1) & set(ids2)
                    if common_ids:
                        mask = mat <= cutoff
                        for i, id1 in enumerate(ids1):
                            for j, id2 in enumerate(ids2):
                                if id1 == id2:
                                    mask[i, j] = False
                                elif id1 in common_ids and id2 in common_ids and id1 > id2:
                                    mask[i, j] = False
                        within = mat[mask]
                    else:
                        within = mat[mat <= cutoff]

                polar_dists = [round(float(d), 2) for d in np.sort(within)]

            if len(polar_dists) == 0 and dist_val > 0 and dist_val <= cutoff:
                polar_dists = [round(float(dist_val), 2)]

            return {
                "success": True,
                "distance_object": name,
                "selection1": selection1,
                "selection2": selection2,
                "cutoff_angstroms": cutoff,
                "candidates_count": len(polar_dists),
                "measured_distances_angstroms": polar_dists,
                "scientific_disclaimer": "These are geometric distance-based polar contact candidates (N/O atoms <= cutoff Å), not experimentally verified hydrogen bonds."
            }

        res = self.executor.run_safe(_exec)
        self.executor.record_command(f"distance {name}, {selection1}, {selection2}, cutoff={cutoff}, mode=2", "find_polar_contact_candidates", {"sel1": selection1, "sel2": selection2, "cutoff": cutoff}, res)
        return res

    def inspect_binding_pocket(
        self,
        ligand_selection: str,
        cutoff: float = 5.0,
        protein_object: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive structural analysis of a ligand binding pocket.
        Automatically restricts protein search to ligand's parent structure when multiple structures are loaded.
        """
        ligand_selection = self.executor.normalize_selection(ligand_selection)

        def _exec():
            lig_count = self.cmd.count_atoms(ligand_selection)
            if lig_count == 0:
                raise ValueError(f"Ligand selection '{ligand_selection}' has 0 atoms.")

            # Auto-detect parent model if not specified to prevent multi-structure contamination
            target_obj = protein_object
            if not target_obj:
                models = []
                self.cmd.iterate(ligand_selection, "models.append(model)", space={"models": models})
                unique_models = sorted(list(set(models)))
                if len(unique_models) == 1:
                    target_obj = unique_models[0]

            protein_sel = f"model {target_obj} and polymer.protein" if target_obj else "polymer.protein"
            pocket_sel = f"byres ({protein_sel} within {cutoff} of ({ligand_selection}))"

            stored_res = set()
            self.cmd.iterate(pocket_sel, "stored_res.add((chain, resi, resn))", space={"stored_res": stored_res})

            pocket_residues = sorted(
                [{"chain": r[0], "resi": str(r[1]), "resn": r[2]} for r in stored_res],
                key=lambda x: (x["chain"], resi_sort_key(x["resi"]))
            )

            # Classify pocket residues
            hydrophobic = [r for r in pocket_residues if r["resn"] in self.HYDROPHOBIC_RESIDUES]
            polar_pos = [r for r in pocket_residues if r["resn"] in self.CHARGED_POSITIVE]
            polar_neg = [r for r in pocket_residues if r["resn"] in self.CHARGED_NEGATIVE]
            aromatic = [r for r in pocket_residues if r["resn"] in self.AROMATIC_RESIDUES]

            # Find polar contact candidates
            polar_obj = "ai_pocket_polar"
            self.cmd.delete(polar_obj)
            dist_val = self.cmd.distance(polar_obj, ligand_selection, pocket_sel, cutoff=3.5, mode=2)

            polar_dists = []
            coords_lig = self.cmd.get_coords(f"({ligand_selection}) and (elem N,O)", 1)
            coords_pocket = self.cmd.get_coords(f"({pocket_sel}) and (elem N,O)", 1)
            if coords_lig is not None and coords_pocket is not None and len(coords_lig) > 0 and len(coords_pocket) > 0:
                diff = coords_lig[:, np.newaxis, :] - coords_pocket[np.newaxis, :, :]
                mat = np.sqrt(np.sum(diff**2, axis=-1))
                within = mat[mat <= 3.5]
                polar_dists = [round(float(d), 2) for d in np.sort(within)]

            if len(polar_dists) == 0 and dist_val > 0 and dist_val <= 3.5:
                polar_dists = [round(float(dist_val), 2)]

            return {
                "success": True,
                "ligand_selection": ligand_selection,
                "cutoff_angstroms": cutoff,
                "parent_protein_object": target_obj,
                "total_pocket_residues": len(pocket_residues),
                "pocket_residues": pocket_residues,
                "composition": {
                    "hydrophobic_residues": [f"{r['resn']}{r['resi']}:{r['chain']}" for r in hydrophobic],
                    "positively_charged_residues": [f"{r['resn']}{r['resi']}:{r['chain']}" for r in polar_pos],
                    "negatively_charged_residues": [f"{r['resn']}{r['resi']}:{r['chain']}" for r in polar_neg],
                    "aromatic_residues": [f"{r['resn']}{r['resi']}:{r['chain']}" for r in aromatic]
                },
                "polar_contact_candidates_count": len(polar_dists),
                "polar_contact_distances": polar_dists,
                "scientific_note": "Binding pocket composition determined by atom distance <= cutoff Å. Polar contacts are geometric candidates."
            }

        return self.executor.run_safe(_exec)
