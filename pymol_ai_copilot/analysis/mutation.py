"""
Mutation parsing, sequence position verification, neighborhood contact analysis, and WT vs Mutant comparison.
"""

import re
from typing import Any, Dict, Optional
import numpy as np
from ..pymol_bridge.executor import PyMOLExecutor
from .contacts import resi_sort_key


class MutationAnalyzer:
    """
    Analyzes point mutations, validates residue identities in PyMOL, and inspects local structural environments.
    """

    AA_3TO1 = {
        "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C",
        "GLN": "Q", "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I",
        "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F", "PRO": "P",
        "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
        "SEC": "U", "PYL": "O"
    }

    AA_1TO3 = {v: k for k, v in AA_3TO1.items()}

    MUTATION_REGEX = re.compile(
        r"^(?:(?P<chain>[A-Za-z0-9]):)?(?P<wt>[A-Za-z]{1,3})(?P<resi>\d+)(?P<mut>[A-Za-z]{1,3})$"
    )

    def __init__(self, executor: Optional[PyMOLExecutor] = None):
        self.executor = executor or PyMOLExecutor()

    @property
    def cmd(self):
        return self.executor.cmd

    def parse_mutation_string(self, text: str) -> Dict[str, Any]:
        """
        Parse strings like 'R132H', 'Arg132His', 'A:R132H', or 'chain A residue 132'.
        """
        clean = text.strip()
        match = self.MUTATION_REGEX.match(clean)
        if match:
            gd = match.groupdict()
            wt_raw = gd["wt"].upper()
            mut_raw = gd["mut"].upper()
            chain = gd["chain"]

            wt_3 = wt_raw if len(wt_raw) == 3 else self.AA_1TO3.get(wt_raw, wt_raw)
            wt_1 = self.AA_3TO1.get(wt_3, wt_raw)

            mut_3 = mut_raw if len(mut_raw) == 3 else self.AA_1TO3.get(mut_raw, mut_raw)
            mut_1 = self.AA_3TO1.get(mut_3, mut_raw)

            return {
                "chain": chain,
                "resi": gd["resi"],
                "wildtype_1": wt_1,
                "wildtype_3": wt_3,
                "mutant_1": mut_1,
                "mutant_3": mut_3,
                "standard_notation": f"{wt_1}{gd['resi']}{mut_1}"
            }

        # Fallback search for number in text
        num_match = re.search(r"\b(\d+)\b", clean)
        resi = num_match.group(1) if num_match else None
        return {
            "chain": None,
            "resi": resi,
            "wildtype_1": None,
            "wildtype_3": None,
            "mutant_1": None,
            "mutant_3": None,
            "standard_notation": clean
        }

    def verify_and_analyze_mutation(
        self,
        mutation_str: str,
        object_name: Optional[str] = None,
        chain: Optional[str] = None,
        radius: float = 5.0
    ) -> Dict[str, Any]:
        """
        Verify residue at sequence position, analyze local contacts, and highlight mutation neighborhood.
        """
        parsed = self.parse_mutation_string(mutation_str)
        target_resi = parsed.get("resi")
        target_chain = chain or parsed.get("chain")

        if not target_resi:
            raise ValueError(f"Could not extract residue number from mutation string: '{mutation_str}'")

        def _exec():
            # Determine object
            obj = object_name
            if not obj:
                objects = self.cmd.get_names("objects")
                if not objects:
                    raise ValueError("No molecular objects loaded in PyMOL session.")
                obj = objects[0]

            # Determine chain if not specified
            ch = target_chain
            if not ch:
                # Find which chain has this residue
                chains = self.cmd.get_chains(obj)
                for candidate in chains:
                    c = self.cmd.count_atoms(f"model {obj} and chain {candidate} and resi {target_resi}")
                    if c > 0:
                        ch = candidate
                        break
                if not ch:
                    ch = chains[0] if chains else ""

            # Check residue identity
            mut_sel = f"model {obj}" + (f" and chain {ch}" if ch else "") + f" and resi {target_resi}"
            atom_count = self.cmd.count_atoms(mut_sel)
            if atom_count == 0:
                raise ValueError(
                    f"Residue {target_resi} (chain '{ch}') not found in object '{obj}'."
                )

            stored_res = []
            self.cmd.iterate(mut_sel, "stored_res.append(resn)", space={"stored_res": stored_res})
            actual_resn = stored_res[0] if stored_res else "UNK"
            actual_1 = self.AA_3TO1.get(actual_resn, "?")

            expected_wt_1 = parsed.get("wildtype_1")
            expected_wt_3 = parsed.get("wildtype_3")

            validation_warning = None
            if expected_wt_3 and actual_resn != expected_wt_3:
                validation_warning = (
                    f"Sequence numbering warning: Mutation specified wild-type '{expected_wt_3}' ({expected_wt_1}), "
                    f"but residue at position {target_resi} (chain {ch}) in '{obj}' is actually '{actual_resn}' ({actual_1})."
                )

            # Analyze neighboring residues within radius
            neighbor_sel = f"byres (model {obj} within {radius} of ({mut_sel})) and not ({mut_sel})"
            stored_neighbors = set()
            self.cmd.iterate(neighbor_sel, "stored_neighbors.add((chain, resi, resn))", space={"stored_neighbors": stored_neighbors})

            neighbor_list = sorted(
                [{"chain": r[0], "resi": str(r[1]), "resn": r[2]} for r in stored_neighbors],
                key=lambda x: (x["chain"], resi_sort_key(x["resi"]))
            )

            # Find polar contact candidates
            dist_name = "ai_mut_contacts"
            self.cmd.delete(dist_name)
            dist_val = self.cmd.distance(dist_name, mut_sel, neighbor_sel, cutoff=3.5, mode=2)
            polar_dists = []

            coords_mut = self.cmd.get_coords(f"({mut_sel}) and (elem N,O)", 1)
            coords_nb = self.cmd.get_coords(f"({neighbor_sel}) and (elem N,O)", 1)
            if coords_mut is not None and coords_nb is not None and len(coords_mut) > 0 and len(coords_nb) > 0:
                diff = coords_mut[:, np.newaxis, :] - coords_nb[np.newaxis, :, :]
                mat = np.sqrt(np.sum(diff**2, axis=-1))
                within = mat[mat <= 3.5]
                polar_dists = [round(float(d), 2) for d in np.sort(within)]

            if len(polar_dists) == 0 and dist_val > 0 and dist_val <= 3.5:
                polar_dists = [round(float(dist_val), 2)]

            return {
                "object": obj,
                "chain": ch,
                "resi": target_resi,
                "actual_residue_3": actual_resn,
                "actual_residue_1": actual_1,
                "expected_wildtype_3": expected_wt_3,
                "intended_mutation": parsed.get("mutant_3"),
                "validation_warning": validation_warning,
                "neighbor_radius_angstroms": radius,
                "neighbor_residues_count": len(neighbor_list),
                "neighbor_residues": neighbor_list,
                "polar_contact_candidates_count": len(polar_dists),
                "polar_contact_distances": polar_dists,
                "scientific_summary": (
                    f"Position {target_resi} (chain {ch}) contains {actual_resn} surrounded by {len(neighbor_list)} residues "
                    f"within {radius} Å, with {len(polar_dists)} geometric polar contact candidate(s)."
                )
            }

        return self.executor.run_safe(_exec)

    def compare_wildtype_and_mutant(
        self,
        wildtype_object: str,
        mutant_object: str,
        mutation_str: str = "",
        chain: str = "A",
        radius: float = 5.0
    ) -> Dict[str, Any]:
        """
        Compare wild-type and mutant structures: sequence-aware alignment, local environment
        reorganization, contact network changes, and geometric displacement quantification.
        """
        parsed = self.parse_mutation_string(mutation_str) if mutation_str else {}
        target_resi = parsed.get("resi")
        target_chain = chain or parsed.get("chain") or "A"

        def _exec():
            all_names = self.cmd.get_names("all")
            if wildtype_object not in all_names:
                raise ValueError(f"Wild-type structure '{wildtype_object}' does not exist.")
            if mutant_object not in all_names:
                raise ValueError(f"Mutant structure '{mutant_object}' does not exist.")

            # Validate chain presence
            wt_chains = self.cmd.get_chains(wildtype_object)
            mut_chains = self.cmd.get_chains(mutant_object)
            if target_chain not in wt_chains:
                raise ValueError(f"Chain '{target_chain}' not found in wild-type '{wildtype_object}' (available: {wt_chains}).")
            if target_chain not in mut_chains:
                raise ValueError(f"Chain '{target_chain}' not found in mutant '{mutant_object}' (available: {mut_chains}).")

            # Sequence-aware structural superposition
            align_res = self.cmd.align(
                f"model {mutant_object} and chain '{target_chain}'",
                f"model {wildtype_object} and chain '{target_chain}'",
                cycles=5,
                cutoff=2.0
            )
            global_rmsd = round(float(align_res[0]), 4)
            aligned_atoms = int(align_res[1])

            # Local analysis at mutation site
            local_analysis = None
            if target_resi:
                wt_res_sel = f"model {wildtype_object} and chain '{target_chain}' and resi '{target_resi}' and not elem H"
                mut_res_sel = f"model {mutant_object} and chain '{target_chain}' and resi '{target_resi}' and not elem H"

                wt_atom_count = self.cmd.count_atoms(wt_res_sel)
                mut_atom_count = self.cmd.count_atoms(mut_res_sel)

                if wt_atom_count == 0:
                    raise ValueError(f"Residue position {target_resi} (chain {target_chain}) does not exist in wild-type '{wildtype_object}'.")
                if mut_atom_count == 0:
                    raise ValueError(f"Residue position {target_resi} (chain {target_chain}) does not exist in mutant '{mutant_object}'. Do not fabricate coordinates.")

                # Residue identities
                wt_resn_list = []
                mut_resn_list = []
                self.cmd.iterate(f"({wt_res_sel}) and name CA", "wt_resn_list.append(resn)", space={"wt_resn_list": wt_resn_list})
                self.cmd.iterate(f"({mut_res_sel}) and name CA", "mut_resn_list.append(resn)", space={"mut_resn_list": mut_resn_list})
                wt_resn = wt_resn_list[0] if wt_resn_list else "UNK"
                mut_resn = mut_resn_list[0] if mut_resn_list else "UNK"

                # C-alpha displacement
                ca_disp = 0.0
                wt_ca = []
                mut_ca = []
                self.cmd.iterate_state(1, f"({wt_res_sel}) and name CA", "wt_ca.append((x, y, z))", space={"wt_ca": wt_ca})
                self.cmd.iterate_state(1, f"({mut_res_sel}) and name CA", "mut_ca.append((x, y, z))", space={"mut_ca": mut_ca})
                if wt_ca and mut_ca:
                    ca_disp = round(float(np.linalg.norm(np.array(wt_ca[0]) - np.array(mut_ca[0]))), 4)

                # Backbone RMSD (N, CA, C, O) computed in NumPy
                bb_atoms = ["N", "CA", "C", "O"]
                wt_bb_coords = {}
                mut_bb_coords = {}
                self.cmd.iterate_state(1, f"({wt_res_sel}) and name N+CA+C+O", "wt_bb_coords[name] = (x, y, z)", space={"wt_bb_coords": wt_bb_coords})
                self.cmd.iterate_state(1, f"({mut_res_sel}) and name N+CA+C+O", "mut_bb_coords[name] = (x, y, z)", space={"mut_bb_coords": mut_bb_coords})

                common_bb = [name for name in bb_atoms if name in wt_bb_coords and name in mut_bb_coords]
                if common_bb:
                    c_wt = np.array([wt_bb_coords[n] for n in common_bb])
                    c_mut = np.array([mut_bb_coords[n] for n in common_bb])
                    bb_rmsd = round(float(np.sqrt(np.mean(np.sum((c_wt - c_mut)**2, axis=-1)))), 4)
                else:
                    bb_rmsd = 0.0

                # Neighbor environment within radius
                wt_nbr_sel = f"byres (model {wildtype_object} and chain '{target_chain}' within {radius} of ({wt_res_sel})) and not ({wt_res_sel}) and name CA"
                mut_nbr_sel = f"byres (model {mutant_object} and chain '{target_chain}' within {radius} of ({mut_res_sel})) and not ({mut_res_sel}) and name CA"

                wt_nbrs = set()
                mut_nbrs = set()
                self.cmd.iterate(wt_nbr_sel, "wt_nbrs.add((resi, resn))", space={"wt_nbrs": wt_nbrs})
                self.cmd.iterate(mut_nbr_sel, "mut_nbrs.add((resi, resn))", space={"mut_nbrs": mut_nbrs})

                wt_nbr_resis = {r[0] for r in wt_nbrs}
                mut_nbr_resis = {r[0] for r in mut_nbrs}

                common_nbrs = sorted(wt_nbr_resis & mut_nbr_resis, key=resi_sort_key)
                lost_nbrs = sorted(wt_nbr_resis - mut_nbr_resis, key=resi_sort_key)
                gained_nbrs = sorted(mut_nbr_resis - wt_nbr_resis, key=resi_sort_key)

                # Compute mean neighbor C-alpha displacement
                nbr_displacements = []
                for n_resi in common_nbrs:
                    c1 = []
                    c2 = []
                    self.cmd.iterate_state(1, f"model {wildtype_object} and chain '{target_chain}' and resi '{n_resi}' and name CA", "c1.append((x, y, z))", space={"c1": c1})
                    self.cmd.iterate_state(1, f"model {mutant_object} and chain '{target_chain}' and resi '{n_resi}' and name CA", "c2.append((x, y, z))", space={"c2": c2})
                    if c1 and c2:
                        nbr_displacements.append(float(np.linalg.norm(np.array(c1[0]) - np.array(c2[0]))))

                mean_nbr_disp = round(float(np.mean(nbr_displacements)), 4) if nbr_displacements else 0.0

                # Polar contact networks computed in NumPy
                def _calc_polar_contacts(obj_name, r_sel):
                    res_coords = []
                    self.cmd.iterate_state(1, f"({r_sel}) and elem N+O", "res_coords.append((x, y, z))", space={"res_coords": res_coords})
                    nbr_coords = []
                    self.cmd.iterate_state(
                        1,
                        f"byres (model {obj_name} within {radius} of ({r_sel})) and not ({r_sel}) and elem N+O",
                        "nbr_coords.append((x, y, z))",
                        space={"nbr_coords": nbr_coords}
                    )
                    if not res_coords or not nbr_coords:
                        return 0
                    arr_res = np.array(res_coords)
                    arr_nbr = np.array(nbr_coords)
                    dists = np.linalg.norm(arr_res[:, None, :] - arr_nbr[None, :, :], axis=-1)
                    return int(np.sum(dists <= 3.5))

                wt_polar_count = _calc_polar_contacts(wildtype_object, wt_res_sel)
                mut_polar_count = _calc_polar_contacts(mutant_object, mut_res_sel)

                local_analysis = {
                    "position": target_resi,
                    "chain": target_chain,
                    "wildtype_residue": wt_resn,
                    "mutant_residue": mut_resn,
                    "ca_displacement_angstrom": ca_disp,
                    "backbone_rmsd_angstrom": bb_rmsd,
                    "neighbor_radius_angstrom": float(radius),
                    "wildtype_neighbors_count": len(wt_nbr_resis),
                    "mutant_neighbors_count": len(mut_nbr_resis),
                    "common_neighbors_count": len(common_nbrs),
                    "lost_neighbors": lost_nbrs,
                    "gained_neighbors": gained_nbrs,
                    "mean_neighbor_ca_displacement_angstrom": mean_nbr_disp,
                    "wildtype_polar_contacts_count": wt_polar_count,
                    "mutant_polar_contacts_count": mut_polar_count,
                    "polar_contacts_delta": mut_polar_count - wt_polar_count
                }

                # Styling for visual comparison
                self.cmd.show("cartoon", f"model {wildtype_object} or model {mutant_object}")
                self.cmd.color("cyan", f"model {wildtype_object}")
                self.cmd.color("orange", f"model {mutant_object}")
                self.cmd.show("sticks", f"({wt_res_sel}) or ({mut_res_sel})")
                self.cmd.util.cnc(f"({wt_res_sel}) or ({mut_res_sel})")
                self.cmd.zoom(f"({wt_res_sel}) expand 6.0")

            # Determine structure origin (experimental vs predicted model)
            origin_type = "predicted_model" if ("af-" in wildtype_object.lower() or "alphafold" in wildtype_object.lower()) else "experimental_structure"

            return {
                "wildtype_object": wildtype_object,
                "mutant_object": mutant_object,
                "chain": target_chain,
                "global_chain_rmsd_angstrom": global_rmsd,
                "aligned_atoms": aligned_atoms,
                "structure_origin": origin_type,
                "local_mutation_comparison": local_analysis,
                "scientific_limitation": (
                    "Geometric structural differences indicate local packing and electrostatic rearrangement, "
                    "but do NOT predict thermodynamic stability changes (ddG), folding kinetics, or biological function "
                    "without experimental binding/stability assays or free-energy simulations."
                )
            }

        res = self.executor.run_safe(_exec)
        self.executor.record_command(
            f"# compare_wildtype_and_mutant {wildtype_object} vs {mutant_object}",
            "compare_wildtype_and_mutant",
            {"wildtype_object": wildtype_object, "mutant_object": mutant_object, "mutation_str": mutation_str},
            res
        )
        return res


