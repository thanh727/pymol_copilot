"""
Mutation parsing, sequence position verification, neighborhood contact analysis, and WT vs Mutant comparison.
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from ..pymol_bridge.executor import PyMOLExecutor


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
                [{"chain": r[0], "resi": r[1], "resn": r[2]} for r in stored_neighbors],
                key=lambda x: (x["chain"], int(x["resi"]) if x["resi"].isdigit() else x["resi"])
            )

            # Find polar contact candidates
            dist_name = "ai_mut_contacts"
            self.cmd.delete(dist_name)
            self.cmd.distance(dist_name, mut_sel, neighbor_sel, cutoff=3.5, mode=2)
            polar_dists = []
            try:
                for item in self.cmd.get_raw_distances(dist_name):
                    polar_dists.append(round(float(item[2]), 2))
            except Exception:
                pass

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
        chain: str = "A",
        resi: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compare wild-type and mutant structures: alignment, global RMSD, local mutation RMSD, and contact differences.
        """
        def _exec():
            # Align mutant onto wildtype
            align_res = self.cmd.align(mutant_object, wildtype_object)
            global_rmsd = round(float(align_res[0]), 3)

            local_analysis = None
            if resi:
                wt_res_sel = f"model {wildtype_object} and chain {chain} and resi {resi}"
                mut_res_sel = f"model {mutant_object} and chain {chain} and resi {resi}"

                if self.cmd.count_atoms(wt_res_sel) > 0 and self.cmd.count_atoms(mut_res_sel) > 0:
                    # In-place coordinate RMSD of CA atom
                    ca_rmsd = round(float(self.cmd.rms_cur(f"({wt_res_sel}) and name CA", f"({mut_res_sel}) and name CA")), 3)

                    # In-place backbone RMSD
                    bb_rmsd = round(float(self.cmd.rms_cur(f"({wt_res_sel}) and name N+CA+C+O", f"({mut_res_sel}) and name N+CA+C+O")), 3)

                    # Get residue identities
                    wt_resn = []
                    mut_resn = []
                    self.cmd.iterate(wt_res_sel, "wt_resn.append(resn)", space={"wt_resn": wt_resn})
                    self.cmd.iterate(mut_res_sel, "mut_resn.append(resn)", space={"mut_resn": mut_resn})

                    local_analysis = {
                        "resi": resi,
                        "chain": chain,
                        "wildtype_resn": wt_resn[0] if wt_resn else "UNK",
                        "mutant_resn": mut_resn[0] if mut_resn else "UNK",
                        "ca_displacement_angstroms": ca_rmsd,
                        "backbone_rmsd_angstroms": bb_rmsd
                    }

            return {
                "wildtype_object": wildtype_object,
                "mutant_object": mutant_object,
                "global_alignment_rmsd": global_rmsd,
                "aligned_atoms": int(align_res[1]),
                "local_mutation_comparison": local_analysis,
                "scientific_interpretation": (
                    f"Superposition of '{mutant_object}' onto '{wildtype_object}' yields a global RMSD of {global_rmsd} Å. "
                    + (f"Local Cα displacement at position {resi} is {local_analysis['ca_displacement_angstroms']} Å." if local_analysis else "")
                )
            }

        return self.executor.run_safe(_exec)

