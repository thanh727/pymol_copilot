"""
Publication-ready visualization presets, styling, and rendering management.
"""

from typing import Any, Dict, List, Optional
from .executor import PyMOLExecutor


class VisualizationPresetManager:
    """
    Manages publication presets and rendering styles for PyMOL.
    """

    COLORBLIND_SAFE_COLORS = [
        "sky_blue", "orange", "bluish_green", "yellow",
        "royal_blue", "vermillion", "reddish_purple"
    ]

    def __init__(self, executor: Optional[PyMOLExecutor] = None):
        self.executor = executor or PyMOLExecutor()

    @property
    def cmd(self):
        return self.executor.cmd

    def setup_publication_lighting(self, bg_color: str = "white") -> None:
        """Configure clean publication lighting and shadows."""
        def _exec():
            self.cmd.bg_color(bg_color)
            self.cmd.set("ray_shadows", 1)
            self.cmd.set("light_count", 2)
            self.cmd.set("ray_trace_mode", 1)  # Normal color with outline
            self.cmd.set("antialias", 2)
            self.cmd.set("ambient", 0.25)
            self.cmd.set("direct", 0.70)
            self.cmd.set("reflect", 0.45)
            self.cmd.set("specular", 0.2)
            self.cmd.set("spec_power", 50)
            self.cmd.set("depth_cue", 1)
            self.cmd.set("fog_start", 0.45)

        self.executor.run_safe(_exec)

    def preset_cartoon_by_chain(self, selection: str = "all", bg_color: str = "white") -> Dict[str, Any]:
        """
        Publication preset: Clean cartoon representation with distinct chain colors.
        """
        def _exec():
            self.cmd.hide("everything", selection)
            self.cmd.show("cartoon", f"({selection}) and polymer")
            self.cmd.show("sticks", f"({selection}) and organic")
            self.cmd.show("nb_spheres", f"({selection}) and inorganic")
            self.cmd.util.color_chains(f"({selection}) and polymer")
            self.cmd.util.cnc(f"({selection}) and organic")
            self.cmd.bg_color(bg_color)
            self.cmd.zoom(selection, buffer=2.0)
            return {"preset": "cartoon_by_chain", "selection": selection, "background": bg_color}

        res = self.executor.run_safe(_exec)
        self.executor.record_command(
            f"# Preset: cartoon_by_chain on {selection}\n"
            f"hide everything, {selection}\n"
            f"show cartoon, ({selection}) and polymer\n"
            f"show sticks, ({selection}) and organic\n"
            f"util.color_chains('({selection}) and polymer')\n"
            f"bg_color {bg_color}",
            "preset_cartoon_by_chain",
            {"selection": selection, "bg_color": bg_color},
            res
        )
        return res

    def preset_binding_pocket(
        self,
        ligand_selection: str,
        cutoff: float = 5.0,
        protein_object: Optional[str] = None,
        show_polar: bool = True
    ) -> Dict[str, Any]:
        """
        Publication preset: Highlight ligand binding pocket with transparent surface,
        interacting residue sticks, and polar contacts.
        """
        def _exec():
            # Verify ligand exists
            lig_count = self.cmd.count_atoms(ligand_selection)
            if lig_count == 0:
                raise ValueError(f"Ligand selection '{ligand_selection}' contains 0 atoms.")

            pocket_sel = "ai_pocket_residues"
            protein_scope = f"model {protein_object} and polymer.protein" if protein_object else "polymer.protein"

            # Select nearby residues within cutoff
            self.cmd.select(pocket_sel, f"byres ({protein_scope} within {cutoff} of ({ligand_selection}))")
            pocket_count = self.cmd.count_atoms(pocket_sel)

            # Style overall protein
            self.cmd.hide("everything", "all")
            self.cmd.show("cartoon", protein_scope)
            self.cmd.color("gray80", protein_scope)

            # Show pocket residues as sticks
            self.cmd.show("sticks", pocket_sel)
            self.cmd.util.cnc(pocket_sel)

            # Show ligand as thick sticks / spheres
            self.cmd.show("sticks", ligand_selection)
            self.cmd.set("stick_radius", 0.28, ligand_selection)
            self.cmd.color("yellow", f"({ligand_selection}) and elem c")
            self.cmd.util.cnc(ligand_selection)

            # Optional polar contacts
            polar_name = "ai_polar_contacts"
            if show_polar:
                self.cmd.delete(polar_name)
                self.cmd.distance(polar_name, ligand_selection, pocket_sel, cutoff=3.5, mode=2)
                self.cmd.set("dash_color", "yellow", polar_name)
                self.cmd.set("dash_width", 2.5, polar_name)

            self.cmd.zoom(f"({ligand_selection}) or ({pocket_sel})", buffer=3.0)
            self.cmd.orient(f"({ligand_selection}) or ({pocket_sel})")

            # Extract list of interacting residues
            stored_pocket = set()
            self.cmd.iterate(pocket_sel, "stored_pocket.add((chain, resi, resn))", space={"stored_pocket": stored_pocket})

            return {
                "preset": "binding_pocket",
                "ligand_selection": ligand_selection,
                "cutoff_angstroms": cutoff,
                "pocket_atoms": pocket_count,
                "interacting_residues": [{"chain": r[0], "resi": r[1], "resn": r[2]} for r in sorted(stored_pocket)],
                "polar_contacts_shown": show_polar
            }

        res = self.executor.run_safe(_exec)
        self.executor.record_command(
            f"# Preset: binding_pocket on {ligand_selection}\n"
            f"select ai_pocket_residues, byres (polymer.protein within {cutoff} of ({ligand_selection}))\n"
            f"show sticks, ai_pocket_residues\n"
            f"show sticks, {ligand_selection}\n"
            f"zoom ({ligand_selection}) or ai_pocket_residues, 3.0",
            "preset_binding_pocket",
            {"ligand": ligand_selection, "cutoff": cutoff},
            res
        )
        return res

    def preset_mutation_neighborhood(
        self,
        mutation_selection: str,
        radius: float = 5.0,
        color_mutation: str = "firebrick"
    ) -> Dict[str, Any]:
        """
        Publication preset: Highlight a mutation site and its immediate structural neighborhood.
        """
        def _exec():
            mut_atoms = self.cmd.count_atoms(mutation_selection)
            if mut_atoms == 0:
                raise ValueError(f"Mutation selection '{mutation_selection}' contains 0 atoms.")

            neighbor_sel = "ai_mutation_neighbors"
            self.cmd.select(neighbor_sel, f"byres (polymer within {radius} of ({mutation_selection})) and not ({mutation_selection})")

            # Style structure
            self.cmd.show("cartoon", "all")
            self.cmd.color("gray85", "all")

            # Mutation residue
            self.cmd.show("sticks", mutation_selection)
            self.cmd.show("spheres", f"({mutation_selection}) and elem c")
            self.cmd.set("sphere_scale", 0.35, f"({mutation_selection}) and elem c")
            self.cmd.color(color_mutation, f"({mutation_selection}) and elem c")
            self.cmd.util.cnc(mutation_selection)

            # Neighbors
            self.cmd.show("sticks", neighbor_sel)
            self.cmd.color("cyan", f"({neighbor_sel}) and elem c")
            self.cmd.util.cnc(neighbor_sel)

            # Polar contacts within neighborhood
            dist_name = "ai_mutation_contacts"
            self.cmd.delete(dist_name)
            self.cmd.distance(dist_name, mutation_selection, neighbor_sel, cutoff=3.6, mode=2)
            self.cmd.set("dash_color", "marine", dist_name)

            self.cmd.zoom(f"({mutation_selection}) or ({neighbor_sel})", buffer=3.0)
            self.cmd.orient(mutation_selection)

            stored_neighbors = set()
            self.cmd.iterate(neighbor_sel, "stored_neighbors.add((chain, resi, resn))", space={"stored_neighbors": stored_neighbors})

            return {
                "preset": "mutation_neighborhood",
                "mutation_selection": mutation_selection,
                "radius_angstroms": radius,
                "neighbor_residues": [{"chain": r[0], "resi": r[1], "resn": r[2]} for r in sorted(stored_neighbors)]
            }

        res = self.executor.run_safe(_exec)
        self.executor.record_command(
            f"# Preset: mutation_neighborhood on {mutation_selection}\n"
            f"select ai_mutation_neighbors, byres (polymer within {radius} of ({mutation_selection})) and not ({mutation_selection})\n"
            f"show sticks, {mutation_selection}\n"
            f"color {color_mutation}, ({mutation_selection}) and elem c\n"
            f"show sticks, ai_mutation_neighbors",
            "preset_mutation_neighborhood",
            {"mutation": mutation_selection, "radius": radius},
            res
        )
        return res

    def preset_epitope(
        self,
        epitope_selection: str,
        color_epitope: str = "magenta",
        surface_context: bool = True
    ) -> Dict[str, Any]:
        """
        Publication preset: Highlight epitope residues clearly against the antigen structure.
        """
        def _exec():
            epi_atoms = self.cmd.count_atoms(epitope_selection)
            if epi_atoms == 0:
                raise ValueError(f"Epitope selection '{epitope_selection}' contains 0 atoms.")

            self.cmd.show("cartoon", "all")
            self.cmd.color("gray85", "all")

            # Epitope visualization
            self.cmd.show("sticks", epitope_selection)
            self.cmd.color(color_epitope, f"({epitope_selection}) and elem c")
            self.cmd.util.cnc(epitope_selection)

            if surface_context:
                self.cmd.show("surface", "all")
                self.cmd.set("transparency", 0.65, "all")
                self.cmd.set("transparency", 0.0, epitope_selection)

            self.cmd.zoom(epitope_selection, buffer=3.0)

            stored_epi = set()
            self.cmd.iterate(epitope_selection, "stored_epi.add((chain, resi, resn))", space={"stored_epi": stored_epi})

            return {
                "preset": "epitope",
                "epitope_selection": epitope_selection,
                "atom_count": epi_atoms,
                "epitope_residues": [{"chain": r[0], "resi": r[1], "resn": r[2]} for r in sorted(stored_epi)]
            }

        res = self.executor.run_safe(_exec)
        self.executor.record_command(
            f"# Preset: epitope on {epitope_selection}\n"
            f"show sticks, {epitope_selection}\n"
            f"color {color_epitope}, ({epitope_selection}) and elem c",
            "preset_epitope",
            {"epitope": epitope_selection, "color": color_epitope},
            res
        )
        return res

