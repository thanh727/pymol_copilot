"""
Structure alignment, superposition, and RMSD computation.
"""

from typing import Any, Dict, List, Optional, Tuple
from ..pymol_bridge.executor import PyMOLExecutor


class StructureAligner:
    """
    Performs sequence-informed and structural alignments, calculating RMSD and structural deviations.
    """

    def __init__(self, executor: Optional[PyMOLExecutor] = None):
        self.executor = executor or PyMOLExecutor()

    @property
    def cmd(self):
        return self.executor.cmd

    def align_structures(
        self,
        mobile: str,
        target: str,
        mobile_selection: str = "",
        target_selection: str = "",
        method: str = "align",
        cutoff: float = 2.0,
        cycles: int = 5
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
        """
        def _exec():
            mob_sel = f"({mobile})" + (f" and ({mobile_selection})" if mobile_selection else "")
            tgt_sel = f"({target})" + (f" and ({target_selection})" if target_selection else "")

            # Verify objects exist
            all_names = self.cmd.get_names("all")
            if mobile not in all_names:
                raise ValueError(f"Mobile structure '{mobile}' does not exist.")
            if target not in all_names:
                raise ValueError(f"Target structure '{target}' does not exist.")

            m = method.lower().strip()
            if m == "align":
                res = self.cmd.align(mob_sel, tgt_sel, cutoff=float(cutoff), cycles=int(cycles))
                # res returns: (rmsd, atoms_aligned, cycles, rmsd_raw, n_atoms)
                rmsd = round(float(res[0]), 3)
                atoms_aligned = int(res[1])
                cycles_run = int(res[2])
                rmsd_raw = round(float(res[3]), 3) if len(res) > 3 else rmsd
                total_atoms = int(res[4]) if len(res) > 4 else atoms_aligned
                return {
                    "method": "align (sequence-guided structural refinement)",
                    "mobile": mobile,
                    "target": target,
                    "rmsd": rmsd,
                    "rmsd_units": "Å",
                    "aligned_atoms": atoms_aligned,
                    "total_initial_atoms": total_atoms,
                    "cycles": cycles_run,
                    "rmsd_raw": rmsd_raw,
                    "cutoff_applied": cutoff
                }
            elif m == "super":
                res = self.cmd.super(mob_sel, tgt_sel, cutoff=float(cutoff), cycles=int(cycles))
                rmsd = round(float(res[0]), 3)
                atoms_aligned = int(res[1])
                cycles_run = int(res[2])
                return {
                    "method": "super (sequence-independent structural superposition)",
                    "mobile": mobile,
                    "target": target,
                    "rmsd": rmsd,
                    "rmsd_units": "Å",
                    "aligned_atoms": atoms_aligned,
                    "cycles": cycles_run,
                    "cutoff_applied": cutoff
                }
            elif m == "cealign":
                res = self.cmd.cealign(tgt_sel, mob_sel)
                # cealign returns dict with 'RMSD', 'alignment_length'
                return {
                    "method": "cealign (combinatorial extension)",
                    "mobile": mobile,
                    "target": target,
                    "rmsd": round(float(res.get("RMSD", 0.0)), 3),
                    "rmsd_units": "Å",
                    "alignment_length": int(res.get("alignment_length", 0))
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
        align_first: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate RMSD between two selections.

        Args:
            mobile_selection: Mobile atom selection.
            target_selection: Target atom selection.
            atom_type: 'CA', 'backbone', or 'all'
            align_first: If True, superimpose first; if False, measure current in-place coordinate RMSD.
        """
        def _exec():
            mob = mobile_selection
            tgt = target_selection

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
                "rmsd": round(rmsd_val, 3),
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
        """
        def _exec():
            # Get CA coordinates and residues for both
            def get_ca_map(obj, ch):
                sel = f"model {obj} and chain {ch} and name CA"
                data = {}
                def store(resi, resn, x, y, z):
                    data[str(resi)] = {"resn": resn, "coord": (x, y, z)}
                self.cmd.iterate_state(1, sel, "store(resi, resn, x, y, z)", space={"store": store})
                return data

            map1 = get_ca_map(structure1, chain1)
            map2 = get_ca_map(structure2, chain2)

            common_resi = sorted(set(map1.keys()) & set(map2.keys()), key=lambda x: int(x) if x.isdigit() else x)
            if not common_resi:
                return {
                    "structure1": structure1,
                    "structure2": structure2,
                    "common_residues_count": 0,
                    "message": "No matching residue numbers found between the two structures."
                }

            deviations = []
            import math
            for r in common_resi:
                c1 = map1[r]["coord"]
                c2 = map2[r]["coord"]
                dist = math.sqrt(sum((c1[i] - c2[i])**2 for i in range(3)))
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
                "structure1": f"{structure1}:{chain1}",
                "structure2": f"{structure2}:{chain2}",
                "compared_residues": len(common_resi),
                "threshold_angstroms": deviation_threshold,
                "deviating_residues_count": len(deviations),
                "deviating_regions": deviations[:20]  # First 20 to avoid giant prompt
            }

        return self.executor.run_safe(_exec)

