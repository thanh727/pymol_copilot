"""
Safe, thread-aware PyMOL execution bridge.
Provides deterministic, audited execution of PyMOL operations without arbitrary code execution.
"""

import os
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional

try:
    from pymol import cmd
except ImportError:
    cmd = None


class PyMOLExecutionError(Exception):
    """Exception raised when a PyMOL command fails."""
    pass


class PyMOLExecutor:
    """
    Executes PyMOL commands with thread safety, validation, and script recording.
    Never executes arbitrary strings via eval() or exec().
    """

    # Common natural-language selection aliases used by local models.
    _SELECTION_ALIASES = {
        "water": "solvent",
        "waters": "solvent",
        "solvent": "solvent",
        "protein": "polymer.protein",
        "proteins": "polymer.protein",
        "ligand": "organic and not solvent",
        "ligands": "organic and not solvent",
        "ion": "inorganic",
        "ions": "inorganic",
        "inorganic": "inorganic",
        "nucleic": "polymer.nucleic",
        "nucleicacid": "polymer.nucleic",
        "hydrogens": "elem H",
        "hydrogen": "elem H",
        "heavy": "not elem H",
        "heavyatoms": "not elem H",
    }
    _SELECTION_KEYWORDS = {
        "all", "none", "polymer", "solvent", "organic", "inorganic",
        "backbone", "sidechain", "name", "resn", "resi", "chain", "model",
        "sele", "byres", "within", "not", "and", "or", "elem", "b", "q",
        "ss", "flag", "color", "rep", "state",
    }

    def __init__(self):
        self._execution_history: List[Dict[str, Any]] = []
        self._recorded_pml_commands: List[str] = []
        self._lock = threading.RLock()

    @property
    def cmd(self):
        if cmd is None:
            raise PyMOLExecutionError("PyMOL is not available or could not be imported.")
        return cmd

    def normalize_selection(self, selection: str) -> str:
        """Turn common shorthand into a valid PyMOL selection.

        Local models frequently emit a bare residue name (``SO4``), a generic
        word (``water``, ``ligand``), or a residue/sequence pair (``SO4 401``).
        PyMOL rejects all of these, which used to burn several agent steps. This
        helper leaves real object/selection names and explicit selection algebra
        untouched, and only rewrites unambiguous shorthands.
        """
        if not isinstance(selection, str):
            return "all"
        text = selection.strip()
        if not text:
            return "all"

        # Strip a single pair of matching quotes around a simple token.
        if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
            inner = text[1:-1].strip()
            if inner and not re.search(r"[\s()]", inner):
                return self.normalize_selection(inner)

        lowered = text.lower()
        alias = self._SELECTION_ALIASES.get(lowered)
        if alias:
            return alias

        try:
            names = list(self.cmd.get_names("all"))
        except Exception:
            names = []
        if text in names:
            return text
        for name in names:
            if name.lower() == lowered:
                return name

        # An explicit PyMOL selection keyword means the text is already valid
        # selection algebra. In particular "resi 441" must never be rewritten
        # as "resn 'RESI' and resi '441'".
        first_token = text.split()[0].lower()
        if first_token in self._SELECTION_KEYWORDS:
            return text

        # Natural-language residue references: "residue 441", "residue G441".
        residue_ref = re.fullmatch(
            r"(?:residue|residues|residue_id)\s+([A-Za-z]?)(-?\d+[A-Za-z]?)",
            text,
            re.IGNORECASE,
        )
        if residue_ref:
            return f"resi '{residue_ref.group(2)}'"

        # Bare one-letter amino acid plus number, e.g. G441 / R132.
        aa_number = re.fullmatch(r"([ACDEFGHIKLMNPQRSTVWY])(-?\d+[A-Za-z]?)", text)
        if aa_number:
            return f"resi '{aa_number.group(2)}'"

        # Residue name plus sequence number: "SO4 401" / "SO4:401".
        pair = re.fullmatch(r"([A-Za-z][A-Za-z0-9]{0,4})\s*[:\s]\s*(-?\d+[A-Za-z]?)", text)
        if pair and pair.group(1).lower() not in self._SELECTION_KEYWORDS:
            return f"resn '{pair.group(1).upper()}' and resi '{pair.group(2)}'"

        # A single bare token of at least two characters is almost always a
        # residue name (SO4, HOH, HEM, MG, ZN, AP5).
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9]{1,4}", text):
            if lowered not in self._SELECTION_KEYWORDS:
                return f"resn '{text.upper()}'"

        return text

    def run_safe(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """
        Run a callable safely. Dispatches to PyMOL GUI thread if available and needed.
        Does not hold internal state lock during blocking GUI dispatch to prevent deadlocks.
        """
        gui_caller = getattr(self.cmd, "_call_in_gui_thread", None)
        if callable(gui_caller):
            try:
                return gui_caller(lambda: func(*args, **kwargs))
            except Exception as e:
                raise PyMOLExecutionError(f"PyMOL command failed: {e}") from e
        else:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                raise PyMOLExecutionError(f"PyMOL command failed: {e}") from e

    def validate_selection(self, selection: str) -> int:
        """Return the atom count for a selection, rejecting empty selections.

        Mutating tools must not report success when PyMOL silently does nothing
        because the model invented a residue name or object.
        """
        def _exec():
            count = self.cmd.count_atoms(selection)
            if count == 0:
                raise ValueError(
                    f"Selection '{selection}' matches 0 atoms in the current "
                    "session. Nothing was changed. Use a valid PyMOL selection "
                    "based on the objects, chains, or residue names reported in "
                    "the session context."
                )
            return count

        return self.run_safe(_exec)

    def record_command(self, pml_line: str, tool_name: str, args: Dict[str, Any], result: Any):
        """Record executed command for history and script generation with thread safety."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        record = {
            "timestamp": timestamp,
            "tool": tool_name,
            "arguments": args,
            "pml": pml_line,
            "result_summary": str(result)[:200]
        }
        with self._lock:
            self._execution_history.append(record)
            if pml_line:
                self._recorded_pml_commands.append(pml_line)

    def get_history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._execution_history)

    def clear_history(self):
        with self._lock:
            self._execution_history.clear()
            self._recorded_pml_commands.clear()

    def get_pml_script(self) -> str:
        """Return all recorded PyMOL commands as a .pml script."""
        header = [
            "# ============================================================",
            "# PyMOL AI Copilot Generated Script",
            f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "# ============================================================",
            ""
        ]
        with self._lock:
            lines = list(self._recorded_pml_commands)
        return "\n".join(header + lines) + "\n"

    # --- Core PyMOL operations with parameter validation ---

    def fetch_structure(self, pdb_id: str, object_name: Optional[str] = None, format: str = "cif") -> Dict[str, Any]:
        """
        Download and load a structure from the Protein Data Bank (PDB).
        Validates accession format, avoids overwriting existing objects, and verifies atom loading.
        """
        import re
        clean_id = pdb_id.strip().lower()
        if not re.match(r"^(?:pdb_)?[0-9][a-z0-9]{3}$", clean_id) and not re.match(r"^af-[a-z0-9]+-f\d+", clean_id):
            if not re.match(r"^[a-z0-9_-]{3,20}$", clean_id):
                raise ValueError(f"Invalid PDB identifier format: '{pdb_id}'. Expected 4-character PDB ID (e.g. '1ubq') or AlphaFold accession.")

        fmt = format.lower().strip()
        if fmt not in ("cif", "pdb", "mmcif"):
            fmt = "cif"
        if fmt == "mmcif":
            fmt = "cif"

        def _exec():
            existing = self.cmd.get_names("objects")
            base = object_name.strip() if object_name else clean_id
            target_name = base
            collision = False
            if target_name in existing:
                collision = True
                idx = 1
                while f"{base}_{idx}" in existing:
                    idx += 1
                target_name = f"{base}_{idx}"

            try:
                fetch_res = self.cmd.fetch(clean_id, name=target_name, type=fmt, async_=0)
            except Exception as e:
                raise PyMOLExecutionError(f"Failed to fetch PDB '{clean_id}': {e}") from e

            if fetch_res == -1 or target_name not in self.cmd.get_names("objects"):
                raise PyMOLExecutionError(
                    f"Unable to download or parse PDB '{clean_id}'. Please verify the PDB accession code and internet connectivity."
                )

            atom_count = self.cmd.count_atoms(target_name)
            if atom_count == 0:
                self.cmd.delete(target_name)
                raise PyMOLExecutionError(f"Fetched PDB '{clean_id}' contains 0 atoms.")

            chains = self.cmd.get_chains(target_name)
            ligand_atoms = self.cmd.count_atoms(f"({target_name}) and organic")
            ligands = []
            if ligand_atoms > 0:
                stored_ligands = set()
                self.cmd.iterate(f"({target_name}) and organic", "stored_ligands.add((resn, resi, chain))", space={"stored_ligands": stored_ligands})
                ligands = [{"resn": r[0], "resi": str(r[1]), "chain": r[2]} for r in sorted(stored_ligands)]

            ligand_msg = ""
            unique_ligs = sorted(list(set(lig["resn"] for lig in ligands))) if ligands else []
            if unique_ligs:
                ligand_msg = f", ligands: {unique_ligs}"

            return {
                "object_name": target_name,
                "pdb_id": clean_id,
                "atom_count": int(atom_count),
                "chains": chains,
                "ligands": ligands,
                "ligand_names": unique_ligs,
                "format": fmt,
                "collision_renamed": collision,
                "message": f"Successfully fetched PDB '{clean_id}' as object '{target_name}' ({atom_count} atoms, chains: {chains}{ligand_msg})."
            }

        res = self.run_safe(_exec)
        self.record_command(f"fetch {clean_id}, name={res['object_name']}, type={fmt}, async=0", "fetch_structure", {"pdb_id": clean_id, "object_name": res["object_name"], "format": fmt}, res)
        return res

    def load_structure(self, file_path: str, object_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Load a molecular structure from a local file.
        Validates path existence, restricts access to approved locations, and checks formats.
        """
        import re
        raw_path = file_path.strip()
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", raw_path):
            raise ValueError(f"Remote URLs are not supported for local file loading: '{file_path}'. Use fetch_structure for PDB accessions.")

        # Resolve symlinks before validation so a link cannot redirect a benign
        # path into a restricted system location.
        abs_path = os.path.realpath(os.path.expanduser(raw_path))

        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"Structure file does not exist: '{file_path}' (resolved to '{abs_path}').")
        if not os.path.isfile(abs_path):
            raise ValueError(f"Path is not a regular file: '{abs_path}'.")

        sensitive_roots = ["/etc", "/private/etc", "/dev", "/proc", "/sys", "/bin", "/sbin", "/usr/bin", "/usr/sbin"]
        for s_root in sensitive_roots:
            if abs_path == s_root or abs_path.startswith(s_root + os.sep):
                raise PermissionError(f"Access to sensitive system path '{abs_path}' is restricted.")

        allowed_exts = {".pdb", ".ent", ".cif", ".mmcif", ".mol2", ".sdf", ".mol", ".pdbqt", ".xyz", ".gro", ".pqr"}
        _, ext = os.path.splitext(abs_path)
        if ext.lower() not in allowed_exts:
            raise ValueError(f"Unsupported molecular file extension '{ext}'. Supported formats: {sorted(allowed_exts)}")

        def _exec():
            existing = self.cmd.get_names("objects")
            if object_name:
                base = object_name.strip()
            else:
                base, _ = os.path.splitext(os.path.basename(abs_path))
            target_name = base
            collision = False
            if target_name in existing:
                collision = True
                idx = 1
                while f"{base}_{idx}" in existing:
                    idx += 1
                target_name = f"{base}_{idx}"

            try:
                self.cmd.load(abs_path, target_name)
            except Exception as e:
                raise PyMOLExecutionError(f"Failed to load structure file '{abs_path}': {e}") from e

            if target_name not in self.cmd.get_names("objects"):
                raise PyMOLExecutionError(f"PyMOL could not load object '{target_name}' from '{abs_path}'.")

            atom_count = self.cmd.count_atoms(target_name)
            if atom_count == 0:
                self.cmd.delete(target_name)
                raise PyMOLExecutionError(f"Loaded file '{abs_path}' contains 0 atoms.")

            chains = self.cmd.get_chains(target_name)
            ligand_atoms = self.cmd.count_atoms(f"({target_name}) and organic")
            ligands = []
            if ligand_atoms > 0:
                stored_ligands = set()
                self.cmd.iterate(f"({target_name}) and organic", "stored_ligands.add((resn, resi, chain))", space={"stored_ligands": stored_ligands})
                ligands = [{"resn": r[0], "resi": str(r[1]), "chain": r[2]} for r in sorted(stored_ligands)]

            ligand_msg = ""
            unique_ligs = sorted(list(set(lig["resn"] for lig in ligands))) if ligands else []
            if unique_ligs:
                ligand_msg = f", ligands: {unique_ligs}"

            return {
                "object_name": target_name,
                "file_path": abs_path,
                "atom_count": int(atom_count),
                "chains": chains,
                "ligands": ligands,
                "ligand_names": unique_ligs,
                "collision_renamed": collision,
                "message": f"Successfully loaded '{abs_path}' as object '{target_name}' ({atom_count} atoms, chains: {chains}{ligand_msg})."
            }

        res = self.run_safe(_exec)
        self.record_command(f"load {abs_path}, {res['object_name']}", "load_structure", {"file_path": abs_path, "object_name": res["object_name"]}, res)
        return res

    def list_objects(self, object_type: str = "all") -> List[str]:
        """List objects loaded in PyMOL."""
        def _exec():
            if object_type == "all":
                return self.cmd.get_names("objects")
            elif object_type == "selections":
                return self.cmd.get_names("selections")
            else:
                return self.cmd.get_names("objects")
        return self.run_safe(_exec)

    def show_representation(self, representation: str, selection: str = "all") -> Dict[str, Any]:
        """Show representation for selection."""
        valid_reps = {
            "cartoon", "sticks", "spheres", "surface", "ribbon",
            "lines", "mesh", "dots", "nonbonded", "nb_spheres"
        }
        rep = representation.lower().strip()
        if rep not in valid_reps:
            raise ValueError(f"Invalid representation: '{representation}'. Valid options: {sorted(valid_reps)}")
        selection = self.normalize_selection(selection)

        def _exec():
            atom_count = self.cmd.count_atoms(selection)
            if atom_count == 0:
                raise ValueError(
                    f"Selection '{selection}' matches 0 atoms in the current session. "
                    "Nothing was displayed. Use a valid PyMOL selection based on the "
                    "loaded objects, chains, or residue names reported in the session context."
                )
            self.cmd.show(rep, selection)
            return {"shown": rep, "selection": selection, "atom_count": atom_count}

        res = self.run_safe(_exec)
        self.record_command(f"show {rep}, {selection}", "show_representation", {"representation": rep, "selection": selection}, res)
        return res

    def hide_representation(self, representation: str = "everything", selection: str = "all") -> Dict[str, Any]:
        """Hide a representation, including semantic water/ion shortcuts."""
        rep = representation.lower().strip()
        selection = self.normalize_selection(selection)

        # "hide water" and "hide ions" are extremely common requests. PyMOL
        # itself only understands representation names, so translate these
        # intents instead of failing with "unknown representation".
        semantic = {
            "water": ("everything", "solvent"),
            "waters": ("everything", "solvent"),
            "solvent": ("everything", "solvent"),
            "ion": ("everything", "inorganic"),
            "ions": ("everything", "inorganic"),
            "inorganic": ("everything", "inorganic"),
            "hydrogen": ("everything", "elem H"),
            "hydrogens": ("everything", "elem H"),
        }
        if rep in semantic:
            hide_rep, hide_selection = semantic[rep]
            if selection != "all":
                hide_selection = f"({selection}) and ({hide_selection})"

            def _exec_semantic():
                self.cmd.hide(hide_rep, hide_selection)
                return {"hidden": hide_rep, "selection": hide_selection}

            res = self.run_safe(_exec_semantic)
            self.record_command(
                f"hide {hide_rep}, {hide_selection}",
                "hide_representation",
                {"representation": rep, "selection": hide_selection},
                res
            )
            return res

        # A request aimed at solvent should hide the whole water object, not
        # only one representation (water is usually shown as nonbonded lines,
        # so "hide sticks, resn HOH" would otherwise leave it visible while
        # reporting success).
        if rep != "everything" and re.search(
            r"\b(?:solvent|hoh|wat|tip3|tip4|spc)\b", selection, re.IGNORECASE
        ):
            rep = "everything"

        def _exec():
            self.cmd.hide(rep, selection)
            return {"hidden": rep, "selection": selection}

        res = self.run_safe(_exec)
        self.record_command(f"hide {rep}, {selection}", "hide_representation", {"representation": rep, "selection": selection}, res)
        return res

    def color_selection(self, color: str, selection: str = "all") -> Dict[str, Any]:
        """Apply color to selection."""
        c = color.strip()
        selection = self.normalize_selection(selection)
        ss_modes = ("by_ss", "secondary_structure", "by_secondary_structure", "byss", "ss", "secondary structure", "by secondary structure")

        def _exec():
            atom_count = self.validate_selection(selection)
            if c.lower() in ss_modes:
                self.cmd.dss(selection)
                self.cmd.util.cbss(selection)
            elif c.lower() == "bychain":
                self.cmd.util.color_chains(selection)
            elif c.lower() == "byelement" or c.lower() == "elem":
                self.cmd.util.cnc(selection)
            elif c.lower().startswith("rainbow"):
                self.cmd.spectrum("count", selection=selection)
            else:
                self.cmd.color(c, selection)
            return {"color": c, "selection": selection, "atom_count": atom_count}

        res = self.run_safe(_exec)

        # Record valid PyMOL command according to color mode
        if c.lower() in ss_modes:
            pml_cmd = f"dss ({selection})\nutil.cbss('({selection})')"
        elif c.lower() == "bychain":
            pml_cmd = f"util.color_chains('({selection})')"
        elif c.lower() in ("byelement", "elem"):
            pml_cmd = f"util.cnc('({selection})')"
        elif c.lower().startswith("rainbow"):
            pml_cmd = f"spectrum count, selection=({selection})"
        else:
            pml_cmd = f"color {c}, ({selection})"

        self.record_command(pml_cmd, "color_selection", {"color": c, "selection": selection}, res)
        return res

    def select(self, name: str, selection: str) -> int:
        """Create a named selection."""
        def _exec():
            atom_count = self.cmd.select(name, selection)
            return int(atom_count)

        res = self.run_safe(_exec)
        self.record_command(f"select {name}, {selection}", "select_residues", {"name": name, "selection": selection}, {"atom_count": res})
        return res

    def zoom(self, selection: str = "all", buffer: float = 2.0) -> None:
        """Zoom to selection."""
        selection = self.normalize_selection(selection)

        def _exec():
            self.validate_selection(selection)
            self.cmd.zoom(selection, buffer=float(buffer))

        self.run_safe(_exec)
        self.record_command(f"zoom {selection}, buffer={buffer}", "zoom_selection", {"selection": selection, "buffer": buffer}, None)

    def orient(self, selection: str = "all") -> None:
        """Orient view along principal axes of selection."""
        selection = self.normalize_selection(selection)

        def _exec():
            self.validate_selection(selection)
            self.cmd.orient(selection)

        self.run_safe(_exec)
        self.record_command(f"orient {selection}", "orient_selection", {"selection": selection}, None)

    def set_background(self, color: str = "white") -> None:
        """Set PyMOL background color."""
        c = color.strip().lower()
        def _exec():
            self.cmd.bg_color(c)

        self.run_safe(_exec)
        self.record_command(f"bg_color {c}", "set_background", {"color": c}, None)

    def set_transparency(self, value: float, selection: str = "all", representation: str = "surface") -> None:
        """Set transparency level (0.0 opaque to 1.0 fully transparent)."""
        val = max(0.0, min(1.0, float(value)))
        rep = representation.lower().strip()
        selection = self.normalize_selection(selection)

        def _exec():
            self.validate_selection(selection)
            if rep == "surface":
                self.cmd.set("transparency", val, selection)
            elif rep == "cartoon":
                self.cmd.set("cartoon_transparency", val, selection)
            elif rep == "sphere":
                self.cmd.set("sphere_transparency", val, selection)
            else:
                self.cmd.set("transparency", val, selection)

        self.run_safe(_exec)
        self.record_command(f"set transparency, {val}, {selection}", "set_transparency", {"value": val, "selection": selection, "representation": rep}, None)

    def reset_view(self) -> None:
        """Reset camera view."""
        def _exec():
            self.cmd.reset()

        self.run_safe(_exec)
        self.record_command("reset", "reset_view", {}, None)

    def export_image(self, filepath: str, width: int = 1920, height: int = 1080, dpi: int = 300, ray: int = 1) -> str:
        """Export ray-traced or OpenGL image."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

        def _exec():
            self.cmd.png(filepath, width=int(width), height=int(height), dpi=int(dpi), ray=int(ray))
            return filepath

        res = self.run_safe(_exec)
        self.record_command(f"png {filepath}, width={width}, height={height}, dpi={dpi}, ray={ray}", "export_png", {"filepath": filepath, "width": width, "height": height, "ray": ray}, res)
        return res

    def save_session(self, filepath: str) -> str:
        """Save PyMOL session file (.pse)."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        if not filepath.endswith(".pse"):
            filepath += ".pse"

        def _exec():
            self.cmd.save(filepath)
            return filepath

        res = self.run_safe(_exec)
        self.record_command(f"save {filepath}", "save_session", {"filepath": filepath}, res)
        return res

