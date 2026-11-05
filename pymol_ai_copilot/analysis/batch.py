"""
Batch Structural Analysis Module.

Aligns multiple molecular structures individually against a reference, enforces consistent
chain mapping and atom-selection policies, calculates cross-structure comparative metrics,
and exports comprehensive summary tables (CSV, JSON), multi-structure overlay images (PNG),
and reproducible session files (PSE).
"""

from typing import Dict, Any, List, Optional
import os
import json
import csv
import time
import numpy as np

from pymol_ai_copilot.pymol_bridge.executor import PyMOLExecutor
from pymol_ai_copilot.analysis.alignment import StructureAligner


class BatchStructureAnalyzer:
    """Performs multi-structure batch alignments and comparative analysis."""

    MAX_BATCH_SIZE: int = 20

    def __init__(self, executor: Optional[PyMOLExecutor] = None):
        self.executor = executor or PyMOLExecutor()
        self.aligner = StructureAligner(self.executor)

    @property
    def cmd(self):
        return self.executor.cmd

    def batch_compare_structures(
        self,
        structure_names: List[str],
        reference_name: str = "",
        chain: str = "A",
        method: str = "align",
        output_dir: str = ""
    ) -> Dict[str, Any]:
        """
        Align a batch of loaded structures against a reference structure.
        Generates comparative metrics table and optional export files.
        """
        def _exec():
            all_names = self.cmd.get_names("all")
            valid_structures = [s for s in structure_names if s in all_names]

            if len(valid_structures) < 2:
                raise ValueError(
                    f"Batch comparison requires at least 2 loaded structures. Provided: {structure_names}, "
                    f"valid in session: {valid_structures}."
                )

            if len(valid_structures) > self.MAX_BATCH_SIZE:
                raise ValueError(
                    f"Batch size {len(valid_structures)} exceeds safety limit ({self.MAX_BATCH_SIZE} structures)."
                )

            # Determine reference structure
            ref = reference_name if reference_name and reference_name in valid_structures else valid_structures[0]
            mobiles = [s for s in valid_structures if s != ref]

            # Colors for distinct visual differentiation
            palette_colors = [
                "cyan", "orange", "marine", "lightpink", "forest", "yellow",
                "purple", "salmon", "splitpea", "deepteal", "warmpink", "sand"
            ]

            results = []
            for i, mob in enumerate(mobiles):
                color_name = palette_colors[i % len(palette_colors)]

                # Execute individual alignment
                aln_res = self.aligner.align_structures(
                    mobile=mob,
                    target=ref,
                    method=method,
                    mobile_chain=chain,
                    target_chain=chain,
                    cycles=5,
                    cutoff=2.0
                )

                # Color the mobile structure distinctly
                self.cmd.color(color_name, f"model {mob}")

                results.append({
                    "structure": mob,
                    "reference": ref,
                    "chain": chain,
                    "method": method,
                    "rmsd_global_ca": aln_res.get("rmsd_global_ca"),
                    "rmsd_refined_ca": aln_res.get("rmsd_refined_ca"),
                    "rmsd_refined_all_atom": aln_res.get("rmsd_refined_all_atom"),
                    "aligned_ca_atoms": aln_res.get("aligned_ca_atoms"),
                    "refined_ca_atoms": aln_res.get("refined_ca_atoms"),
                    "matched_residues": aln_res.get("matched_residues"),
                    "color_assigned": color_name
                })

            # Color reference structure neutral white/gray
            self.cmd.color("gray80", f"model {ref}")
            self.cmd.show("cartoon", "all")
            self.cmd.orient("all")

            # Optional exports
            exported_files = {}
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

                # 1. JSON
                json_path = os.path.join(output_dir, "batch_comparison.json")
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump({"reference": ref, "results": results}, f, indent=2)
                exported_files["json"] = json_path

                # 2. CSV
                csv_path = os.path.join(output_dir, "batch_comparison.csv")
                with open(csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "Structure", "Reference", "Chain", "Method",
                        "Global Ca RMSD (Å)", "Refined Ca RMSD (Å)", "Refined All-Atom RMSD (Å)",
                        "Aligned Ca Atoms", "Refined Ca Atoms", "Matched Residues", "Color"
                    ])
                    for r in results:
                        writer.writerow([
                            r["structure"], r["reference"], r["chain"], r["method"],
                            r["rmsd_global_ca"], r["rmsd_refined_ca"], r["rmsd_refined_all_atom"],
                            r["aligned_ca_atoms"], r["refined_ca_atoms"], r["matched_residues"],
                            r["color_assigned"]
                        ])
                exported_files["csv"] = csv_path

                # 3. PNG overlay
                png_path = os.path.join(output_dir, "batch_overlay.png")
                self.cmd.png(png_path, width=1280, height=720, ray=0)
                exported_files["png"] = png_path

                # 4. PSE session
                pse_path = os.path.join(output_dir, "batch_session.pse")
                self.cmd.save(pse_path)
                exported_files["pse"] = pse_path

            return {
                "reference_structure": ref,
                "chain_analyzed": chain,
                "total_structures_analyzed": len(valid_structures),
                "comparisons_count": len(results),
                "results": results,
                "exported_files": exported_files,
                "scientific_limitation": (
                    "Batch structural alignment provides consistent rigid-body pairwise superposition against "
                    "a common reference. Variations in relative RMSD across the batch reflect conformational diversity "
                    "or domain movements; evaluate individual residue displacement profiles for detailed mechanistic insight."
                )
            }

        res = self.executor.run_safe(_exec)
        self.executor.record_command(
            f"# batch_compare_structures {structure_names}",
            "batch_compare_structures",
            {"structure_names": structure_names, "reference_name": reference_name},
            res
        )
        return res

