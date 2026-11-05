"""
Structure alignment, superposition, and RMSD computation.
"""

from typing import Any, Dict, List, Optional, Tuple
from ..pymol_bridge.executor import PyMOLExecutor
from .contacts import resi_sort_key


class StructureAligner:
    """
    Performs sequence-informed and structural alignments, calculating RMSD and structural deviations.
    """

    def __init__(self, executor: Optional[PyMOLExecutor] = None):
        self.executor = executor or PyMOLExecutor()

    @property
    def cmd(self):
        return self.executor.cmd

    def _extract_alignment_details(self, aln_obj: str, mob_sel: str, tgt_sel: str, mobile: str, target: str):
        """Extract unique matched residues and 1-to-1 residue correspondence from alignment object."""
        try:
            raw_aln = self.cmd.get_raw_alignment(aln_obj)
            m_atoms = {}
            t_atoms = {}
            self.cmd.iterate(mob_sel, "m_atoms[index] = (chain, resi, resn)", space={"m_atoms": m_atoms})
            self.cmd.iterate(tgt_sel, "t_atoms[index] = (chain, resi, resn)", space={"t_atoms": t_atoms})

            pairs = []
            seen = set()
            m_resis = set()
            for p1, p2 in raw_aln:
                m_info, t_info = None, None
                for model, idx in (p1, p2):
                    if model == mobile and idx in m_atoms:
                        m_info = m_atoms[idx]
                    elif model == target and idx in t_atoms:
                        t_info = t_atoms[idx]
                if m_info and t_info:
                    pair_key = (m_info, t_info)
                    if pair_key not in seen:
                        seen.add(pair_key)
                        m_resis.add(m_info)
                        pairs.append({
                            "mobile": f"{m_info[0]}:{m_info[2]}{m_info[1]}",
                            "target": f"{t_info[0]}:{t_info[2]}{t_info[1]}"
                        })
            return len(m_resis), pairs
        except Exception:
            return 0, []

    def _count_matched_residues(self, aln_obj: str, mob_sel: str, mobile: str) -> int:
        """Count unique residues present in a PyMOL alignment object."""
        try:
            raw_aln = self.cmd.get_raw_alignment(aln_obj)
            idx_to_resi = {}
            self.cmd.iterate(mob_sel, "idx_to_resi[index] = (resi, chain)", space={"idx_to_resi": idx_to_resi})
            matched_resis = set()
            for p1, p2 in raw_aln:
                for model, idx in (p1, p2):
                    if model == mobile and idx in idx_to_resi:
                        matched_resis.add(idx_to_resi[idx])
            return len(matched_resis)
        except Exception:
            return 0

    def align_structures(
        self,
        mobile: str,
        target: str,
        mobile_selection: str = "",
        target_selection: str = "",
        method: str = "align",
        cutoff: float = 2.0,
        cycles: int = 5,
        mobile_chain: str = "",
        target_chain: str = ""
    ) -> Dict[str, Any]:
        """
        Align mobile structure onto target structure using PyMOL's align, super, or cealign.

        Args:
            mobile: Name of object to move.
            target: Name of static reference object.
            mobile_selection: Optional sub-selection on mobile (default full object).
            target_selection: Optional sub-selection on target (default full object).
            method: 'align' (sequence-guided + outlier rejection), 'super' (sequence-independent), or 'cealign' (combinatorial extension).
            cutoff: Outlier rejection distance in angstroms.
            cycles: Maximum refinement cycles.
            mobile_chain: Optional specific chain for mobile structure (e.g. 'A').
            target_chain: Optional specific chain for target reference structure (e.g. 'A').
        """
        def _exec():
            mob_parts = [f"model {mobile}"]
            if mobile_chain:
                mob_parts.append(f"chain '{mobile_chain}'")
            if mobile_selection:
                mob_parts.append(f"({mobile_selection})")
            mob_sel = " and ".join(mob_parts)

            tgt_parts = [f"model {target}"]
            if target_chain:
                tgt_parts.append(f"chain '{target_chain}'")
            if target_selection:
                tgt_parts.append(f"({target_selection})")
            tgt_sel = " and ".join(tgt_parts)

            # Verify objects exist
            all_names = self.cmd.get_names("all")
            if mobile not in all_names:
                raise ValueError(f"Mobile structure '{mobile}' does not exist.")
            if target not in all_names:
                raise ValueError(f"Target structure '{target}' does not exist.")

            m = method.lower().strip()
            if m == "align":
                aln_obj = f"_aln_{mobile}_{target}"
                res = self.cmd.align(mob_sel, tgt_sel, cutoff=float(cutoff), cycles=int(cycles), object=aln_obj)
                # res returns: (rmsd, atoms_aligned, cycles, rmsd_raw, n_atoms)
                rmsd_refined_all_atom = round(float(res[0]), 4)
                atoms_aligned = int(res[1])
                cycles_run = int(res[2])
                rmsd_raw_all_atom = round(float(res[3]), 4) if len(res) > 3 else rmsd_refined_all_atom
                total_atoms = int(res[4]) if len(res) > 4 else atoms_aligned

                matched_residues, correspondence = self._extract_alignment_details(aln_obj, mob_sel, tgt_sel, mobile, target)
                self.cmd.delete(aln_obj)

                # Compute unrefined global Ca RMSD (cycles=0) for transparent reporting
                res_ca_global = self.cmd.align(f"({mob_sel}) and name CA", f"({tgt_sel}) and name CA", cycles=0)
                rmsd_global_ca = round(float(res_ca_global[0]), 4)
                aligned_ca_count = int(res_ca_global[1])

                # Compute refined Ca RMSD with outlier rejection cycles
                res_ca_refined = self.cmd.align(f"({mob_sel}) and name CA", f"({tgt_sel}) and name CA", cutoff=float(cutoff), cycles=int(cycles))
                rmsd_refined_ca = round(float(res_ca_refined[0]), 4)
                refined_ca_atoms = int(res_ca_refined[1])

                return {
                    "method": "align (sequence-guided structural refinement)",
                    "mobile": mobile,
                    "target": target,
                    "mobile_chain": mobile_chain or "all",
                    "target_chain": target_chain or "all",
                    "rmsd": rmsd_refined_all_atom,
                    "rmsd_refined_core": rmsd_refined_all_atom,
                    "rmsd_refined_all_atom": rmsd_refined_all_atom,
                    "rmsd_refined_ca": rmsd_refined_ca,
                    "rmsd_global_ca": rmsd_global_ca,
                    "rmsd_raw_all_atom": rmsd_raw_all_atom,
                    "rmsd_units": "Å",
                    "aligned_atoms": atoms_aligned,
                    "aligned_all_atoms": atoms_aligned,
                    "total_initial_atoms": total_atoms,
                    "aligned_ca_atoms": aligned_ca_count,
                    "refined_ca_atoms": refined_ca_atoms,
                    "matched_residues": aligned_ca_count,
                    "refined_core_residues": matched_residues,
                    "residue_correspondence_count": len(correspondence),
                    "residue_correspondence": correspondence,
                    "cycles": cycles_run,
                    "rmsd_raw": rmsd_raw_all_atom,
                    "cutoff_applied": cutoff
                }
            elif m == "super":
                aln_obj = f"_sup_{mobile}_{target}"
                res = self.cmd.super(mob_sel, tgt_sel, cutoff=float(cutoff), cycles=int(cycles), object=aln_obj)
                rmsd_refined_all_atom = round(float(res[0]), 4)
                atoms_aligned = int(res[1])
                cycles_run = int(res[2])
                rmsd_raw_all_atom = round(float(res[3]), 4) if len(res) > 3 else rmsd_refined_all_atom
                total_atoms = int(res[4]) if len(res) > 4 else atoms_aligned

                matched_residues, correspondence = self._extract_alignment_details(aln_obj, mob_sel, tgt_sel, mobile, target)
                self.cmd.delete(aln_obj)

                res_ca_global = self.cmd.super(f"({mob_sel}) and name CA", f"({tgt_sel}) and name CA", cycles=0)
                rmsd_global_ca = round(float(res_ca_global[0]), 4)
                aligned_ca_count = int(res_ca_global[1])

                res_ca_refined = self.cmd.super(f"({mob_sel}) and name CA", f"({tgt_sel}) and name CA", cutoff=float(cutoff), cycles=int(cycles))
                rmsd_refined_ca = round(float(res_ca_refined[0]), 4)
                refined_ca_atoms = int(res_ca_refined[1])

                return {
                    "method": "super (sequence-independent structural superposition)",
                    "mobile": mobile,
                    "target": target,
                    "mobile_chain": mobile_chain or "all",
                    "target_chain": target_chain or "all",
                    "rmsd": rmsd_refined_all_atom,
                    "rmsd_refined_core": rmsd_refined_all_atom,
                    "rmsd_refined_all_atom": rmsd_refined_all_atom,
                    "rmsd_refined_ca": rmsd_refined_ca,
                    "rmsd_global_ca": rmsd_global_ca,
                    "rmsd_raw_all_atom": rmsd_raw_all_atom,
                    "rmsd_units": "Å",
                    "aligned_atoms": atoms_aligned,
                    "aligned_all_atoms": atoms_aligned,
                    "total_initial_atoms": total_atoms,
                    "aligned_ca_atoms": aligned_ca_count,
                    "refined_ca_atoms": refined_ca_atoms,
                    "matched_residues": aligned_ca_count,
                    "refined_core_residues": matched_residues,
                    "residue_correspondence_count": len(correspondence),
                    "residue_correspondence": correspondence,
                    "cycles": cycles_run,
                    "rmsd_raw": rmsd_raw_all_atom,
                    "cutoff_applied": cutoff
                }
            elif m == "cealign":
                aln_obj = f"_ce_{mobile}_{target}"
                res = self.cmd.cealign(tgt_sel, mob_sel, object=aln_obj)
                # cealign returns dict with 'RMSD', 'alignment_length'
                rmsd_ce = round(float(res.get("RMSD", 0.0)), 4)
                aln_len = int(res.get("alignment_length", 0))
                matched_residues, correspondence = self._extract_alignment_details(aln_obj, mob_sel, tgt_sel, mobile, target)
                self.cmd.delete(aln_obj)
                return {
                    "method": "cealign (combinatorial extension)",
                    "mobile": mobile,
                    "target": target,
                    "mobile_chain": mobile_chain or "all",
                    "target_chain": target_chain or "all",
                    "rmsd": rmsd_ce,
                    "rmsd_refined_core": rmsd_ce,
                    "rmsd_refined_all_atom": rmsd_ce,
                    "rmsd_refined_ca": rmsd_ce,
                    "rmsd_global_ca": rmsd_ce,
                    "rmsd_units": "Å",
                    "aligned_atoms": aln_len,
                    "aligned_all_atoms": aln_len,
                    "aligned_ca_atoms": aln_len,
                    "refined_ca_atoms": aln_len,
                    "alignment_length": aln_len,
                    "matched_residues": matched_residues or aln_len,
                    "residue_correspondence_count": len(correspondence) or aln_len,
                    "residue_correspondence": correspondence
                }
            else:
                raise ValueError(f"Unknown alignment method: '{method}'. Choose 'align', 'super', or 'cealign'.")

        res = self.executor.run_safe(_exec)
        pml_cmd = f"{method} {mobile}, {target}, cutoff={cutoff}, cycles={cycles}"
        self.executor.record_command(pml_cmd, "align_structures", {"mobile": mobile, "target": target, "method": method}, res)
        return res

    def calculate_rmsd(
        self,
        mobile_selection: str,
        target_selection: str,
        atom_type: str = "CA",
        align_first: bool = False,
        mobile_chain: str = "",
        target_chain: str = ""
    ) -> Dict[str, Any]:
        """
        Calculate RMSD between two selections.

        Args:
            mobile_selection: Mobile atom selection.
            target_selection: Target atom selection.
            atom_type: 'CA', 'backbone', or 'all'
            align_first: If True, superimpose first; if False, measure current in-place coordinate RMSD.
            mobile_chain: Optional specific chain filter for mobile selection.
            target_chain: Optional specific chain filter for target selection.
        """
        def _exec():
            mob = mobile_selection
            tgt = target_selection

            if mobile_chain:
                mob = f"({mob}) and chain '{mobile_chain}'"
            if target_chain:
                tgt = f"({tgt}) and chain '{target_chain}'"

            if atom_type.upper() == "CA":
                mob = f"({mob}) and name CA"
                tgt = f"({tgt}) and name CA"
            elif atom_type.lower() == "backbone":
                mob = f"({mob}) and name N+CA+C+O"
                tgt = f"({tgt}) and name N+CA+C+O"

            count_mob = self.cmd.count_atoms(mob)
            count_tgt = self.cmd.count_atoms(tgt)

            if count_mob == 0:
                raise ValueError(f"Mobile selection '{mob}' contains 0 atoms.")
            if count_tgt == 0:
                raise ValueError(f"Target selection '{tgt}' contains 0 atoms.")

            if align_first:
                res = self.cmd.align(mob, tgt)
                rmsd_val = float(res[0])
                atoms = int(res[1])
                mode = "superimposed RMSD"
            else:
                # rms_cur computes RMSD without modifying coordinates
                rmsd_val = float(self.cmd.rms_cur(mob, tgt))
                atoms = min(count_mob, count_tgt)
                mode = "in-place coordinate RMSD"

            return {
                "rmsd": round(rmsd_val, 4),
                "units": "Å",
                "atom_filter": atom_type,
                "atoms_compared": atoms,
                "calculation_mode": mode,
                "mobile_selection": mob,
                "target_selection": tgt
            }

        return self.executor.run_safe(_exec)

    def compare_residues(
        self,
        structure1: str,
        structure2: str,
        chain1: str = "A",
        chain2: str = "A",
        deviation_threshold: float = 2.0
    ) -> Dict[str, Any]:
        """
        Compare corresponding residues in two structures, identifying high-deviation regions (> threshold).
        Handles missing or unassigned chains and insertion codes gracefully.
        """
        def _exec():
            # Resolve actual chains in structures
            chains_s1 = self.cmd.get_chains(structure1)
            chains_s2 = self.cmd.get_chains(structure2)

            eff_ch1 = chain1
            if eff_ch1 not in chains_s1 and chains_s1:
                eff_ch1 = chains_s1[0]

            eff_ch2 = chain2
            if eff_ch2 not in chains_s2 and chains_s2:
                eff_ch2 = chains_s2[0]

            # Get CA coordinates and residues for both
            def get_ca_map(obj, ch):
                sel_parts = [f"model {obj}", "name CA"]
                if ch:
                    sel_parts.append(f"chain '{ch}'")
                sel = " and ".join(sel_parts)

                data = {}
                def store(resi, resn, x, y, z):
                    data[str(resi)] = {"resn": resn, "coord": (x, y, z)}
                self.cmd.iterate_state(1, sel, "store(resi, resn, x, y, z)", space={"store": store})
                return data

            map1 = get_ca_map(structure1, eff_ch1)
            map2 = get_ca_map(structure2, eff_ch2)

            common_resi = sorted(set(map1.keys()) & set(map2.keys()), key=resi_sort_key)
            if not common_resi:
                return {
                    "success": True,
                    "structure1": f"{structure1}:{eff_ch1}",
                    "structure2": f"{structure2}:{eff_ch2}",
                    "common_residues_count": 0,
                    "message": "No matching residue numbers found between the two structures."
                }

            deviations = []
            import math
            max_dist = 0.0
            all_dists = []
            for r in common_resi:
                c1 = map1[r]["coord"]
                c2 = map2[r]["coord"]
                dist = math.sqrt(sum((c1[i] - c2[i])**2 for i in range(3)))
                all_dists.append(dist)
                if dist > max_dist:
                    max_dist = dist
                resn1 = map1[r]["resn"]
                resn2 = map2[r]["resn"]
                if dist >= deviation_threshold:
                    deviations.append({
                        "resi": r,
                        "resn1": resn1,
                        "resn2": resn2,
                        "distance_angstroms": round(dist, 2),
                        "mutation": f"{resn1}->{resn2}" if resn1 != resn2 else "conserved"
                    })

            return {
                "success": True,
                "structure1": f"{structure1}:{eff_ch1}",
                "structure2": f"{structure2}:{eff_ch2}",
                "compared_residues": len(common_resi),
                "threshold_angstroms": deviation_threshold,
                "deviating_residues_count": len(deviations),
                "deviating_regions": deviations[:20],  # First 20 to avoid giant prompt
                "max_displacement": round(max_dist, 3),
                "average_displacement": round(sum(all_dists) / len(all_dists), 3) if all_dists else 0.0
            }

        return self.executor.run_safe(_exec)

