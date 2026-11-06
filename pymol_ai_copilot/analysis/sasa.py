"""
Solvent Accessibility Analysis Module.

Calculates absolute solvent-accessible surface area (SASA, in Å²) and relative solvent
accessibility (RSA, %) using PyMOL's native dot-solvent engine and published empirical
maximum accessibility references (Tien et al., 2013).
Supports per-residue breakdown, B-factor mapping, surface coloring, and cross-structure comparisons.
"""

from typing import Dict, Any, Optional
import os
import json
import csv

from ..pymol_bridge.executor import PyMOLExecutor
from .contacts import resi_sort_key


# Empirical theoretical maximum accessible surface area (MaxSASA in Å²)
# Reference: Tien et al., PLoS ONE 8(11): e80635 (2013), Gly-X-Gly tripeptide model.
TIEN_MAX_SASA: Dict[str, float] = {
    "ALA": 129.0,
    "ARG": 274.0,
    "ASN": 195.0,
    "ASP": 193.0,
    "CYS": 167.0,
    "GLN": 225.0,
    "GLU": 223.0,
    "GLY": 104.0,
    "HIS": 224.0,
    "ILE": 197.0,
    "LEU": 201.0,
    "LYS": 236.0,
    "MET": 224.0,
    "PHE": 240.0,
    "PRO": 159.0,
    "SER": 155.0,
    "THR": 172.0,
    "TRP": 285.0,
    "TYR": 263.0,
    "VAL": 174.0
}


class SASAAnalyzer:
    """Analyzes solvent-accessible surface areas (SASA) and residue exposure."""

    def __init__(self, executor: Optional[PyMOLExecutor] = None):
        self.executor = executor or PyMOLExecutor()

    @property
    def cmd(self):
        return self.executor.cmd

    def calculate_sasa(
        self,
        object_name: str,
        selection: str = "",
        probe_radius: float = 1.4,
        dot_density: int = 2
    ) -> Dict[str, Any]:
        """
        Calculate total and per-residue Solvent Accessible Surface Area (SASA) in Å²
        and Relative Solvent Accessibility (RSA) in %.
        """
        def _exec():
            all_names = self.cmd.get_names("all")
            if object_name not in all_names:
                raise ValueError(f"Object '{object_name}' does not exist.")

            # Configure PyMOL surface area calculation parameters
            self.cmd.set("dot_solvent", 1)
            self.cmd.set("solvent_radius", float(probe_radius))
            self.cmd.set("dot_density", int(dot_density))

            target_sel = f"model {object_name}"
            if selection:
                target_sel += f" and ({selection})"

            # PyMOL native: get_area with load_b=1 computes atomic SASA in C and puts it in the b-factor column
            total_area = round(float(self.cmd.get_area(target_sel, load_b=1)), 2)

            # Accumulate atomic SASA into per-residue totals
            res_areas = {}
            self.cmd.iterate(
                f"({target_sel}) and polymer.protein",
                "res_areas[(chain, resi, resn)] = res_areas.get((chain, resi, resn), 0.0) + b",
                space={"res_areas": res_areas}
            )

            residue_sasa_list = []
            buried_count = 0
            intermediate_count = 0
            exposed_count = 0

            # Sort residues naturally by chain, then resi
            sorted_keys = sorted(
                res_areas.keys(),
                key=lambda x: (x[0], resi_sort_key(x[1]))
            )

            for chain, resi, resn in sorted_keys:
                r_clean = resn.strip().upper()
                r_area = round(float(res_areas[(chain, resi, resn)]), 2)

                max_ref = TIEN_MAX_SASA.get(r_clean, 200.0)
                rsa = round((r_area / max_ref) * 100.0, 1)

                if rsa < 20.0:
                    classification = "buried"
                    buried_count += 1
                elif rsa < 50.0:
                    classification = "intermediate"
                    intermediate_count += 1
                else:
                    classification = "exposed"
                    exposed_count += 1

                residue_sasa_list.append({
                    "chain": chain,
                    "residue_number": resi,
                    "residue_name": r_clean,
                    "sasa_angstrom2": r_area,
                    "rsa_percent": rsa,
                    "max_reference_sasa": max_ref,
                    "classification": classification
                })

            return {
                "object": object_name,
                "selection_applied": selection or "all",
                "total_sasa_angstrom2": total_area,
                "probe_radius_angstrom": float(probe_radius),
                "dot_density": int(dot_density),
                "residues_analyzed": len(residue_sasa_list),
                "buried_residues_count": buried_count,
                "intermediate_residues_count": intermediate_count,
                "exposed_residues_count": exposed_count,
                "residues": residue_sasa_list,
                "scientific_limitation": (
                    "Absolute SASA is reported in Å² for static crystal coordinates. Relative SASA (RSA) "
                    "uses empirical tripeptide MaxSASA references (Tien et al., 2013). Conformational uncertainty, "
                    "backbone breathing, and crystal packing effects should be considered before classifying residues "
                    "as permanently accessible or buried in solution."
                )
            }

        res = self.executor.run_safe(_exec)
        self.executor.record_command(f"# calculate_sasa {object_name}", "calculate_sasa", {"object_name": object_name, "probe_radius": probe_radius}, res)
        return res

    def map_sasa_to_structure(
        self,
        object_name: str,
        selection: str = "",
        probe_radius: float = 1.4,
        palette: str = "blue_white_red",
        representation: str = "surface"
    ) -> Dict[str, Any]:
        """
        Calculate SASA, load atomic area values into the B-factor column, and color
        the molecular surface or cartoon using a continuous color spectrum.
        """
        def _exec():
            all_names = self.cmd.get_names("all")
            if object_name not in all_names:
                raise ValueError(f"Object '{object_name}' does not exist.")

            self.cmd.set("dot_solvent", 1)
            self.cmd.set("solvent_radius", float(probe_radius))

            target_sel = f"model {object_name}"
            if selection:
                target_sel += f" and ({selection})"

            # PyMOL native: get_area with load_b=1 puts atomic SASA into b-factors
            self.cmd.get_area(target_sel, load_b=1)

            rep = representation.lower().strip()
            if rep == "surface":
                self.cmd.show("surface", target_sel)
                self.cmd.set("surface_quality", 1)
            else:
                self.cmd.show("cartoon", target_sel)

            self.cmd.spectrum("b", palette, target_sel)

            return {
                "object": object_name,
                "selection": target_sel,
                "mapped_to": "b_factor",
                "palette": palette,
                "representation": rep,
                "status": f"SASA successfully loaded into B-factors and visualized via {palette} spectrum."
            }

        res = self.executor.run_safe(_exec)
        self.executor.record_command(f"# map_sasa_to_structure {object_name}", "map_sasa_to_structure", {"object_name": object_name}, res)
        return res

    def compare_sasa(
        self,
        object1: str,
        object2: str,
        chain1: str = "A",
        chain2: str = "A",
        probe_radius: float = 1.4
    ) -> Dict[str, Any]:
        """
        Compare residue SASA between two structures (e.g., apo vs holo, or wild-type vs mutant).
        Calculates per-residue Delta SASA = SASA(object1) - SASA(object2).
        """
        def _exec():
            sasa1 = self.calculate_sasa(object1, selection=f"chain '{chain1}'", probe_radius=probe_radius)
            sasa2 = self.calculate_sasa(object2, selection=f"chain '{chain2}'", probe_radius=probe_radius)

            res_map1 = {r["residue_number"]: r for r in sasa1.get("residues", [])}
            res_map2 = {r["residue_number"]: r for r in sasa2.get("residues", [])}

            common_resis = sorted(set(res_map1.keys()) & set(res_map2.keys()), key=resi_sort_key)

            comparisons = []
            large_changes = []

            for resi in common_resis:
                r1 = res_map1[resi]
                r2 = res_map2[resi]
                a1 = r1["sasa_angstrom2"]
                a2 = r2["sasa_angstrom2"]
                delta = round(a1 - a2, 2)

                item = {
                    "residue_number": resi,
                    "residue_name1": r1["residue_name"],
                    "residue_name2": r2["residue_name"],
                    "sasa_object1": a1,
                    "sasa_object2": a2,
                    "delta_sasa_angstrom2": delta,
                    "rsa_object1": r1["rsa_percent"],
                    "rsa_object2": r2["rsa_percent"]
                }
                comparisons.append(item)
                if abs(delta) >= 20.0:
                    large_changes.append(item)

            return {
                "object1": object1,
                "object2": object2,
                "chain1": chain1,
                "chain2": chain2,
                "probe_radius_angstrom": float(probe_radius),
                "total_sasa_object1": sasa1.get("total_sasa_angstrom2", 0.0),
                "total_sasa_object2": sasa2.get("total_sasa_angstrom2", 0.0),
                "residues_compared": len(comparisons),
                "significant_changes_count": len(large_changes),
                "significant_changes": large_changes,
                "all_comparisons": comparisons
            }

        res = self.executor.run_safe(_exec)
        self.executor.record_command(f"# compare_sasa {object1} {object2}", "compare_sasa", {"object1": object1, "object2": object2}, res)
        return res

    def export_sasa_table(
        self,
        sasa_data: Dict[str, Any],
        output_path: str,
        export_format: str = "json"
    ) -> Dict[str, Any]:
        """Export SASA analysis results to JSON or CSV."""
        fmt = export_format.lower().strip()
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        if fmt == "csv":
            residues = sasa_data.get("residues", [])
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Chain", "Residue Number", "Residue Name",
                    "SASA (Å²)", "RSA (%)", "Max Ref SASA (Å²)", "Classification"
                ])
                for r in residues:
                    writer.writerow([
                        r.get("chain"),
                        r.get("residue_number"),
                        r.get("residue_name"),
                        r.get("sasa_angstrom2"),
                        r.get("rsa_percent"),
                        r.get("max_reference_sasa"),
                        r.get("classification")
                    ])
        else:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(sasa_data, f, indent=2)

        return {
            "output_path": output_path,
            "format": fmt,
            "bytes_written": os.path.getsize(output_path),
            "success": True
        }
