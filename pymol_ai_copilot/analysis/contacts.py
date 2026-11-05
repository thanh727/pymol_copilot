"""
Intermolecular and intramolecular contact analysis, distances, and binding pockets.
"""

from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np
from ..pymol_bridge.executor import PyMOLExecutor


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

    def calculate_distances(
        self,
        selection1: str,
        selection2: str,
        cutoff: float = 5.0,
        name: str = "ai_dist"
    ) -> Dict[str, Any]:
        """
        Measure pairwise atomic distances between two selections within cutoff.
        """
        def _exec():
            c1 = self.cmd.count_atoms(selection1)
            c2 = self.cmd.count_atoms(selection2)
            if c1 == 0 or c2 == 0:
                raise ValueError(f"One or both selections contain 0 atoms ({selection1}: {c1}, {selection2}: {c2}).")

            self.cmd.delete(name)
            # cmd.distance creates visual measurement object in PyMOL
            dist_val = self.cmd.distance(name, selection1, selection2, cutoff=float(cutoff), mode=0)

            # Extract coordinates to compute detailed contact pair distribution
            coords1 = self.cmd.get_coords(selection1, 1)
            coords2 = self.cmd.get_coords(selection2, 1)

            pairs_within_cutoff = []
            if coords1 is not None and coords2 is not None and len(coords1) > 0 and len(coords2) > 0:
                # Pairwise distance matrix using numpy
                diff = coords1[:, np.newaxis, :] - coords2[np.newaxis, :, :]
                dist_matrix = np.sqrt(np.sum(diff**2, axis=-1))

                within = dist_matrix[dist_matrix <= cutoff]
                pairs_within_cutoff = [round(float(d), 2) for d in np.sort(within)]

            pair_count = len(pairs_within_cutoff)
            if pair_count == 0 and dist_val > 0 and dist_val <= cutoff:
                pairs_within_cutoff = [round(float(dist_val), 2)]
                pair_count = 1

            min_dist = pairs_within_cutoff[0] if pairs_within_cutoff else None
            mean_dist = round(float(np.mean(pairs_within_cutoff)), 2) if pairs_within_cutoff else min_dist

            return {
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
        """
        def _exec():
            t_count = self.cmd.count_atoms(target_selection)
            if t_count == 0:
                raise ValueError(f"Target selection '{target_selection}' has 0 atoms.")

            query = f"byres (({surrounding_scope}) within {cutoff} of ({target_selection})) and not ({target_selection})"
            atom_count = self.cmd.count_atoms(query)

            stored_res = set()
            self.cmd.iterate(query, "stored_res.add((chain, resi, resn))", space={"stored_res": stored_res})

            res_list = sorted([{"chain": r[0], "resi": r[1], "resn": r[2]} for r in stored_res], key=lambda x: (x["chain"], int(x["resi"]) if x["resi"].isdigit() else x["resi"]))

            return {
                "target_selection": target_selection,
                "cutoff_angstroms": cutoff,
                "surrounding_scope": surrounding_scope,
                "total_atoms": atom_count,
                "residue_count": len(res_list),
                "residues": res_list
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
        def _exec():
            c1 = self.cmd.count_atoms(selection1)
            c2 = self.cmd.count_atoms(selection2)
            if c1 == 0 or c2 == 0:
                raise ValueError(f"Selection has 0 atoms ({selection1}: {c1}, {selection2}: {c2}).")

            self.cmd.delete(name)
            # mode=2 in cmd.distance finds polar contacts (donor/acceptor geometry)
            dist_val = self.cmd.distance(name, selection1, selection2, cutoff=float(cutoff), mode=2)

            # Polar atoms filter
            polar1_sel = f"({selection1}) and (elem N,O)"
            polar2_sel = f"({selection2}) and (elem N,O)"

            coords1 = self.cmd.get_coords(polar1_sel, 1)
            coords2 = self.cmd.get_coords(polar2_sel, 1)

            polar_dists = []
            if coords1 is not None and coords2 is not None and len(coords1) > 0 and len(coords2) > 0:
                diff = coords1[:, np.newaxis, :] - coords2[np.newaxis, :, :]
                mat = np.sqrt(np.sum(diff**2, axis=-1))
                within = mat[mat <= cutoff]
                polar_dists = [round(float(d), 2) for d in np.sort(within)]

            if len(polar_dists) == 0 and dist_val > 0 and dist_val <= cutoff:
                polar_dists = [round(float(dist_val), 2)]

            return {
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
        """
        def _exec():
            lig_count = self.cmd.count_atoms(ligand_selection)
            if lig_count == 0:
                raise ValueError(f"Ligand selection '{ligand_selection}' has 0 atoms.")

            protein_sel = f"model {protein_object} and polymer.protein" if protein_object else "polymer.protein"
            pocket_sel = f"byres ({protein_sel} within {cutoff} of ({ligand_selection}))"

            stored_res = set()
            self.cmd.iterate(pocket_sel, "stored_res.add((chain, resi, resn))", space={"stored_res": stored_res})

            pocket_residues = sorted([{"chain": r[0], "resi": r[1], "resn": r[2]} for r in stored_res], key=lambda x: (x["chain"], int(x["resi"]) if x["resi"].isdigit() else x["resi"]))

            # Classify pocket residues
            hydrophobic = [r for r in pocket_residues if r["resn"] in self.HYDROPHOBIC_RESIDUES]
            polar_pos = [r for r in pocket_residues if r["resn"] in self.CHARGED_POSITIVE]
            polar_neg = [r for r in pocket_residues if r["resn"] in self.CHARGED_NEGATIVE]
            aromatic = [r for r in pocket_residues if r["resn"] in self.AROMATIC_RESIDUES]

            # Find polar contact candidates
            polar_obj = "ai_pocket_polar"
            self.cmd.delete(polar_obj)
            dist_val = self.cmd.distance(polar_obj, ligand_selection, pocket_sel, cutoff=3.5, mode=2)

            # Measure distances
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
                "ligand_selection": ligand_selection,
                "cutoff_angstroms": cutoff,
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
