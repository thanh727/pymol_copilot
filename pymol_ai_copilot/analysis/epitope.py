"""
Epitope Structural Mapping Module.

Maps linear peptide sequences and discontinuous residue sets to 3D macromolecular structures.
Resolves residue numbering offsets and chain assignments, computes surface accessibility (SASA/RSA),
quantifies spatial clustering and 3D compactness, and provides publication-grade visualizations.
"""

from typing import Dict, Any, List, Optional, Tuple, Set
import os
import json
import csv
import re
import numpy as np

from pymol_ai_copilot.pymol_bridge.executor import PyMOLExecutor
from pymol_ai_copilot.analysis.sasa import SASAAnalyzer, TIEN_MAX_SASA


AA3_TO_1: Dict[str, str] = {
    "ALA": "A", "CYS": "C", "ASP": "D", "GLU": "E", "PHE": "F",
    "GLY": "G", "HIS": "H", "ILE": "I", "LYS": "K", "LEU": "L",
    "MET": "M", "ASN": "N", "PRO": "P", "GLN": "Q", "ARG": "R",
    "SER": "S", "THR": "T", "VAL": "V", "TRP": "W", "TYR": "Y"
}


class EpitopeMapper:
    """Maps epitopes to 3D structures and analyzes spatial presentation and accessibility."""

    def __init__(self, executor: Optional[PyMOLExecutor] = None):
        self.executor = executor or PyMOLExecutor()
        self.sasa_analyzer = SASAAnalyzer(self.executor)

    @property
    def cmd(self):
        return self.executor.cmd

    def map_epitope_sequence(
        self,
        object_name: str,
        epitope_sequence: str = "",
        residue_list: str = "",
        chain: str = ""
    ) -> Dict[str, Any]:
        """
        Map a linear peptide sequence or explicit residue identifier list to the protein structure.
        Resolves chain correspondence and numbering offsets.
        """
        def _exec():
            all_names = self.cmd.get_names("all")
            if object_name not in all_names:
                raise ValueError(f"Object '{object_name}' does not exist.")

            # Discover available chains
            chains = self.cmd.get_chains(object_name)
            if not chains:
                raise ValueError(f"No chains found in object '{object_name}'.")

            clean_seq = epitope_sequence.strip().upper()
            clean_res_list = residue_list.strip()

            target_chains = [chain.strip()] if chain.strip() and chain.strip() in chains else chains

            # Case A: Linear sequence provided
            if clean_seq:
                matched_chain = None
                matched_resis = []
                matched_pos = -1

                for ch in target_chains:
                    # Extract sequence for chain
                    res_tuples = []
                    self.cmd.iterate(
                        f"model {object_name} and chain '{ch}' and polymer.protein and name CA",
                        "res_tuples.append((resi, resn))",
                        space={"res_tuples": res_tuples}
                    )
                    ch_seq = "".join(AA3_TO_1.get(r[1].strip().upper(), "X") for r in res_tuples)

                    pos = ch_seq.find(clean_seq)
                    if pos != -1:
                        matched_chain = ch
                        matched_pos = pos
                        matched_resis = [res_tuples[i][0] for i in range(pos, pos + len(clean_seq))]
                        break

                if not matched_chain:
                    raise ValueError(
                        f"Linear epitope sequence '{clean_seq}' not found in object '{object_name}' "
                        f"(checked chains: {target_chains})."
                    )

                mapping_type = "linear_sequence"
                res_numbers = matched_resis
                eff_chain = matched_chain

            # Case B: Residue list / range provided (e.g. "40,41,42,43" or "A:40-45" or "40-45")
            elif clean_res_list:
                eff_chain = target_chains[0]
                m_ch = re.match(r"^([A-Za-z0-9]):(.*)", clean_res_list)
                if m_ch:
                    eff_chain = m_ch.group(1)
                    clean_res_list = m_ch.group(2)

                res_numbers = []
                for part in clean_res_list.split(","):
                    p = part.strip()
                    if "-" in p:
                        start_str, end_str = p.split("-", 1)
                        if start_str.isdigit() and end_str.isdigit():
                            res_numbers.extend([str(i) for i in range(int(start_str), int(end_str) + 1)])
                    elif p:
                        res_numbers.append(p)

                # Validate residue existence in object
                valid_resis = set()
                self.cmd.iterate(
                    f"model {object_name} and chain '{eff_chain}' and polymer.protein and name CA",
                    "valid_resis.add(resi)",
                    space={"valid_resis": valid_resis}
                )
                filtered_resis = [r for r in res_numbers if r in valid_resis]
                if not filtered_resis:
                    raise ValueError(f"None of the specified residues {res_numbers} exist in chain '{eff_chain}'.")
                res_numbers = filtered_resis
                mapping_type = "residue_list"
            else:
                raise ValueError("Must provide either 'epitope_sequence' or 'residue_list'.")

            # Extract 3D coordinates of epitope CA atoms
            sel_str = f"model {object_name} and chain '{eff_chain}' and resi {'+'.join(res_numbers)} and name CA"
            coords = []
            ca_labels = []
            self.cmd.iterate_state(
                1,
                sel_str,
                "coords.append((x, y, z)); ca_labels.append(f'{resn}{resi}')",
                space={"coords": coords, "ca_labels": ca_labels}
            )

            if not coords:
                raise ValueError(f"No C-alpha atoms found for mapped epitope selection '{sel_str}'.")

            coords_arr = np.array(coords, dtype=float)
            centroid = np.mean(coords_arr, axis=0)

            # Spatial compactness: pairwise C-alpha distance matrix
            if len(coords_arr) > 1:
                pw_dists = np.linalg.norm(coords_arr[:, None, :] - coords_arr[None, :, :], axis=-1)
                i_upper = np.triu_indices(len(coords_arr), k=1)
                upper_dists = pw_dists[i_upper]
                max_span = float(np.max(upper_dists))
                mean_dist = float(np.mean(upper_dists))
                is_clustered = bool(max_span <= 30.0)
            else:
                max_span = 0.0
                mean_dist = 0.0
                is_clustered = True

            # Calculate accessibility of epitope residues
            sasa_res = self.sasa_analyzer.calculate_sasa(object_name, selection=f"chain '{eff_chain}'")
            sasa_lookup = {r["residue_number"]: r for r in sasa_res.get("residues", [])}

            epitope_sasa_list = []
            total_epi_sasa = 0.0
            exposed_epi_resis = 0

            for r_num in res_numbers:
                r_info = sasa_lookup.get(r_num, {"sasa_angstrom2": 0.0, "rsa_percent": 0.0, "classification": "unknown"})
                total_epi_sasa += r_info["sasa_angstrom2"]
                if r_info["rsa_percent"] >= 20.0:
                    exposed_epi_resis += 1
                epitope_sasa_list.append({
                    "residue_number": r_num,
                    "residue_name": r_info.get("residue_name", ""),
                    "sasa_angstrom2": r_info["sasa_angstrom2"],
                    "rsa_percent": r_info["rsa_percent"],
                    "classification": r_info["classification"]
                })

            avg_rsa = round(float(np.mean([r["rsa_percent"] for r in epitope_sasa_list])), 1) if epitope_sasa_list else 0.0

            return {
                "object": object_name,
                "chain": eff_chain,
                "mapping_type": mapping_type,
                "mapped_residues_count": len(res_numbers),
                "residue_numbers": res_numbers,
                "epitope_selection": f"model {object_name} and chain '{eff_chain}' and resi {'+'.join(res_numbers)}",
                "spatial_centroid": [round(float(c), 3) for c in centroid],
                "maximum_span_angstrom": round(max_span, 3),
                "mean_pairwise_distance_angstrom": round(mean_dist, 3),
                "is_spatially_clustered": is_clustered,
                "total_epitope_sasa_angstrom2": round(total_epi_sasa, 2),
                "average_rsa_percent": avg_rsa,
                "exposed_residues_count": exposed_epi_resis,
                "residue_accessibility": epitope_sasa_list,
                "scientific_limitation": (
                    "Epitope mapping identifies structural localization, 3D spatial compactness, and solvent accessibility. "
                    "Surface exposure alone does NOT establish antigenicity, antibody binding affinity, or in vivo "
                    "immunogenicity without immunological, serological, or structural binding assays."
                )
            }

        res = self.executor.run_safe(_exec)
        self.executor.record_command(f"# map_epitope {object_name}", "map_epitope_sequence", {"object_name": object_name}, res)
        return res

    def visualize_epitope(
        self,
        object_name: str,
        chain: str,
        residue_numbers: List[str],
        representation: str = "surface_highlight"
    ) -> Dict[str, Any]:
        """
        Visualize mapped epitope on the protein structure.
        Highlights epitope in magenta/orange against a neutral background.
        """
        def _exec():
            epi_sel = f"model {object_name} and chain '{chain}' and resi {'+'.join(residue_numbers)}"
            prot_sel = f"model {object_name} and polymer.protein"

            self.cmd.show("cartoon", prot_sel)
            self.cmd.color("gray80", prot_sel)

            rep = representation.lower().strip()
            if rep == "spheres":
                self.cmd.show("spheres", epi_sel)
                self.cmd.color("magenta", epi_sel)
            else:
                self.cmd.show("surface", epi_sel)
                self.cmd.color("magenta", epi_sel)
                self.cmd.show("sticks", epi_sel)

            self.cmd.zoom(f"({epi_sel}) expand 6.0")
            self.cmd.orient(f"({epi_sel}) expand 6.0")

            return {
                "object": object_name,
                "chain": chain,
                "epitope_selection": epi_sel,
                "representation": rep,
                "status": "Epitope visualization rendered successfully."
            }

        res = self.executor.run_safe(_exec)
        self.executor.record_command(f"# visualize_epitope {object_name}", "visualize_epitope", {"object_name": object_name}, res)
        return res

