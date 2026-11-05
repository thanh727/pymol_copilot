"""
Ligand Interaction Analysis Module.

Identifies bound ligands, distinguishes them from solvent and crystallization additives,
computes minimum heavy-atom distances and geometric polar contacts, generates pocket
visualizations, and exports contact tables.
"""

from typing import Dict, Any, List, Optional, Set
import os
import json
import csv
import numpy as np

from pymol_ai_copilot.pymol_bridge.executor import PyMOLExecutor


# Common non-biologically-relevant ligands, solvent, crystallization additives, and buffer ions
SOLVENT_RESIDUES: Set[str] = {
    "HOH", "WAT", "H2O", "TIP", "TIP3", "DOD"
}

INORGANIC_IONS: Set[str] = {
    "NA", "CL", "K", "MG", "CA", "ZN", "MN", "FE", "FE2", "CU", "CO", "NI",
    "BR", "IOD", "SO4", "PO4", "NO3", "NH4", "ACT", "FMT"
}

CRYSTALLIZATION_ADDITIVES: Set[str] = {
    "EDO", "GOL", "PEG", "PGE", "PG4", "1PE", "2PE", "DMS", "MPD", "CIT",
    "TRS", "BME", "MES", "EPE", "HEPES", "IPA", "ACE", "NAG", "BOG", "LDA"
}

ALL_EXCLUDED_HETATMS: Set[str] = SOLVENT_RESIDUES | INORGANIC_IONS | CRYSTALLIZATION_ADDITIVES


class LigandAnalyzer:
    """Performs protein-ligand contact analysis and pocket inspection."""

    def __init__(self, executor: Optional[PyMOLExecutor] = None):
        self.executor = executor or PyMOLExecutor()

    @property
    def cmd(self):
        return self.executor.cmd

    def identify_ligands(self, object_name: str) -> Dict[str, Any]:
        """
        Identify bound biologically relevant ligands in an object, distinguishing them from
        crystallization additives, solvents, and common buffer salts.
        """
        def _exec():
            all_names = self.cmd.get_names("all")
            if object_name not in all_names:
                raise ValueError(f"Object '{object_name}' does not exist.")

            # Discover all non-polymer hetero groups (including solvents/additives to classify)
            het_res = set()
            self.cmd.iterate(
                f"{object_name} and not polymer",
                "het_res.add((resn, resi, chain))",
                space={"het_res": het_res}
            )

            ligands = []
            excluded_additives = []

            for resn, resi, chain in sorted(het_res, key=lambda x: (x[2], int(x[1]) if x[1].isdigit() else x[1])):
                clean_resn = resn.strip().upper()
                sel = f"{object_name} and chain '{chain}' and resi '{resi}' and resn '{resn}'"
                atom_count = self.cmd.count_atoms(sel)
                heavy_count = self.cmd.count_atoms(f"({sel}) and not elem H")

                item = {
                    "resn": clean_resn,
                    "resi": resi,
                    "chain": chain,
                    "atom_count": atom_count,
                    "heavy_atom_count": heavy_count,
                    "selection": sel
                }

                if clean_resn in ALL_EXCLUDED_HETATMS or heavy_count <= 1:
                    item["reason"] = (
                        "solvent" if clean_resn in SOLVENT_RESIDUES else
                        "ion" if clean_resn in INORGANIC_IONS else
                        "crystallization_additive_or_buffer"
                    )
                    excluded_additives.append(item)
                else:
                    ligands.append(item)

            return {
                "object": object_name,
                "total_ligands": len(ligands),
                "ligands": ligands,
                "excluded_additives_count": len(excluded_additives),
                "excluded_additives": excluded_additives
            }

        res = self.executor.run_safe(_exec)
        self.executor.record_command(f"# identify_ligands {object_name}", "identify_ligands", {"object_name": object_name}, res)
        return res

    def analyze_ligand_interactions(
        self,
        object_name: str,
        ligand_resn: str = "",
        ligand_resi: str = "",
        ligand_chain: str = "",
        cutoff: float = 4.0,
        altloc: str = "A"
    ) -> Dict[str, Any]:
        """
        Analyze protein residues interacting with a specific ligand within a cutoff.
        Calculates minimum heavy-atom distances and identifies geometric polar contact candidates.
        """
        def _exec():
            all_names = self.cmd.get_names("all")
            if object_name not in all_names:
                raise ValueError(f"Object '{object_name}' does not exist.")

            # If ligand identifier is missing, attempt to discover the primary ligand
            target_resn = ligand_resn.strip().upper()
            target_resi = str(ligand_resi).strip()
            target_chain = ligand_chain.strip()

            if not target_resn:
                disc = self.identify_ligands(object_name)
                ligs = disc.get("ligands", [])
                if not ligs:
                    raise ValueError(f"No bound organic ligands identified in '{object_name}'.")
                target_resn = ligs[0]["resn"]
                target_resi = ligs[0]["resi"]
                target_chain = ligs[0]["chain"]

            # Construct ligand selection with alternate conformation handling
            lig_parts = [f"model {object_name}", f"resn '{target_resn}'"]
            if target_resi:
                lig_parts.append(f"resi '{target_resi}'")
            if target_chain:
                lig_parts.append(f"chain '{target_chain}'")
            if altloc:
                lig_parts.append(f"(alt ''+{altloc})")
            lig_parts.append("not elem H")
            lig_sel = " and ".join(lig_parts)

            lig_atom_count = self.cmd.count_atoms(lig_sel)
            if lig_atom_count == 0:
                raise ValueError(f"Ligand selection '{lig_sel}' contains 0 atoms.")

            # Extract ligand heavy atom coordinates and element types
            lig_coords = []
            lig_atoms = []
            self.cmd.iterate_state(
                1,
                lig_sel,
                "lig_coords.append((x, y, z)); lig_atoms.append((name, elem, resn, resi, chain))",
                space={"lig_coords": lig_coords, "lig_atoms": lig_atoms}
            )
            lig_coords_arr = np.array(lig_coords, dtype=float)

            # Discover contacting protein residues within cutoff
            prot_sel = f"model {object_name} and polymer.protein"
            if altloc:
                prot_sel += f" and (alt ''+{altloc})"

            pocket_sel = f"({prot_sel}) within {float(cutoff)} of ({lig_sel})"
            byres_pocket_sel = f"byres ({pocket_sel})"

            # Collect unique residues in pocket
            res_tuples = set()
            self.cmd.iterate(
                f"({byres_pocket_sel}) and name CA",
                "res_tuples.add((resn, resi, chain))",
                space={"res_tuples": res_tuples}
            )

            contacts = []
            total_polar_contacts = 0

            for r_resn, r_resi, r_chain in sorted(res_tuples, key=lambda x: (x[2], int(x[1]) if x[1].isdigit() else x[1])):
                r_parts = [
                    f"model {object_name}",
                    f"chain '{r_chain}'",
                    f"resi '{r_resi}'",
                    f"resn '{r_resn}'",
                    "not elem H"
                ]
                if altloc:
                    r_parts.append(f"(alt ''+{altloc})")
                r_sel = " and ".join(r_parts)

                r_coords = []
                r_atoms = []
                self.cmd.iterate_state(
                    1,
                    r_sel,
                    "r_coords.append((x, y, z)); r_atoms.append((name, elem))",
                    space={"r_coords": r_coords, "r_atoms": r_atoms}
                )
                if not r_coords:
                    continue

                r_coords_arr = np.array(r_coords, dtype=float)

                # Pairwise distance matrix: dist[i, j] = || r_coords[i] - lig_coords[j] ||
                dist_matrix = np.linalg.norm(r_coords_arr[:, None, :] - lig_coords_arr[None, :, :], axis=-1)
                min_dist = float(np.min(dist_matrix))

                # Identify polar contact candidates (N/O pairs within 3.5 Å)
                polar_candidates = []
                for i, (r_name, r_elem) in enumerate(r_atoms):
                    if r_elem in ("N", "O"):
                        for j, (l_name, l_elem, _, _, _) in enumerate(lig_atoms):
                            if l_elem in ("N", "O") and dist_matrix[i, j] <= 3.5:
                                d_val = round(float(dist_matrix[i, j]), 3)
                                polar_candidates.append({
                                    "residue_atom": r_name,
                                    "ligand_atom": l_name,
                                    "distance_angstrom": d_val
                                })
                                total_polar_contacts += 1

                # Classify contact type
                contact_type = "polar" if polar_candidates else "hydrophobic_or_vdw"

                contacts.append({
                    "residue_name": r_resn,
                    "residue_number": r_resi,
                    "chain": r_chain,
                    "min_distance_angstrom": round(min_dist, 3),
                    "contact_type": contact_type,
                    "polar_contacts": polar_candidates,
                    "contact_atoms_count": int(np.sum(dist_matrix <= float(cutoff)))
                })

            contacts.sort(key=lambda x: x["min_distance_angstrom"])

            return {
                "object": object_name,
                "ligand_resn": target_resn,
                "ligand_resi": target_resi,
                "ligand_chain": target_chain,
                "ligand_heavy_atoms": len(lig_coords),
                "cutoff_angstrom": float(cutoff),
                "altloc_handled": altloc,
                "contacting_residues_count": len(contacts),
                "polar_contacts_count": total_polar_contacts,
                "contacts": contacts,
                "scientific_limitation": (
                    "Geometric proximity (< 4.0 Å) indicates structural neighborhood and geometric polar contact "
                    "candidates, but does NOT constitute thermodynamic proof of binding affinity, free energy "
                    "contribution, or direct hydrogen bonding without energetic and electrostatic evaluation."
                )
            }

        res = self.executor.run_safe(_exec)
        self.executor.record_command(
            f"# analyze_ligand_interactions {object_name} {ligand_resn}:{ligand_resi}",
            "analyze_ligand_interactions",
            {"object_name": object_name, "ligand_resn": ligand_resn, "cutoff": cutoff},
            res
        )
        return res

    def visualize_ligand_pocket(
        self,
        object_name: str,
        ligand_resn: str,
        ligand_resi: str = "",
        ligand_chain: str = "",
        cutoff: float = 4.0,
        show_contacts: bool = True
    ) -> Dict[str, Any]:
        """
        Configure PyMOL representations for publication-quality ligand pocket inspection:
        cartoon protein, sticks for ligand and pocket residues, dashed polar contacts, and zoom.
        """
        def _exec():
            # Build selections
            lig_parts = [f"model {object_name}", f"resn '{ligand_resn}'"]
            if ligand_resi:
                lig_parts.append(f"resi '{ligand_resi}'")
            if ligand_chain:
                lig_parts.append(f"chain '{ligand_chain}'")
            lig_sel = " and ".join(lig_parts)

            prot_sel = f"model {object_name} and polymer.protein"
            pocket_sel = f"byres (({prot_sel}) within {float(cutoff)} of ({lig_sel}))"

            # 1. Base representations
            self.cmd.show("cartoon", prot_sel)
            self.cmd.color("slate", prot_sel)

            # 2. Ligand styling: thick sticks, yellow carbons
            self.cmd.show("sticks", lig_sel)
            self.cmd.color("yellow", lig_sel)
            self.cmd.util.cnc(lig_sel)

            # 3. Pocket residues styling: sticks, cyan carbons
            self.cmd.show("sticks", pocket_sel)
            self.cmd.color("cyan", pocket_sel)
            self.cmd.util.cnc(pocket_sel)

            # 4. Optional polar contacts
            contact_obj = f"_contacts_{object_name}_{ligand_resn}"
            if show_contacts:
                self.cmd.distance(
                    contact_obj,
                    f"({lig_sel}) and elem N+O",
                    f"({pocket_sel}) and elem N+O",
                    cutoff=3.5,
                    mode=2
                )
                self.cmd.show("dashes", contact_obj)
                self.cmd.color("yellow", contact_obj)

            # 5. Orient and zoom
            self.cmd.zoom(f"({lig_sel}) expand {float(cutoff) + 1.0}")
            self.cmd.orient(f"({lig_sel}) expand {float(cutoff) + 1.0}")

            return {
                "object": object_name,
                "ligand_selection": lig_sel,
                "pocket_selection": pocket_sel,
                "contacts_object": contact_obj if show_contacts else "",
                "status": "Pocket visualization rendered successfully."
            }

        res = self.executor.run_safe(_exec)
        self.executor.record_command(
            f"# visualize_ligand_pocket {object_name} {ligand_resn}",
            "visualize_ligand_pocket",
            {"object_name": object_name, "ligand_resn": ligand_resn},
            res
        )
        return res

    def export_contacts_table(
        self,
        contacts_data: Dict[str, Any],
        output_path: str,
        export_format: str = "json"
    ) -> Dict[str, Any]:
        """Export contact table to JSON or CSV."""
        fmt = export_format.lower().strip()
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        if fmt == "csv":
            contacts = contacts_data.get("contacts", [])
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Residue Name", "Residue Number", "Chain",
                    "Min Distance (Å)", "Contact Type", "Contact Atoms", "Polar Pairs"
                ])
                for c in contacts:
                    polar_str = "; ".join([f"{p['residue_atom']}-{p['ligand_atom']}:{p['distance_angstrom']}Å" for p in c.get("polar_contacts", [])])
                    writer.writerow([
                        c.get("residue_name"),
                        c.get("residue_number"),
                        c.get("chain"),
                        c.get("min_distance_angstrom"),
                        c.get("contact_type"),
                        c.get("contact_atoms_count"),
                        polar_str
                    ])
        else:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(contacts_data, f, indent=2)

        return {
            "output_path": output_path,
            "format": fmt,
            "bytes_written": os.path.getsize(output_path),
            "success": True
        }
