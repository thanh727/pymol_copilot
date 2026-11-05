"""
Safe, thread-aware PyMOL execution bridge.
Provides deterministic, audited execution of PyMOL operations without arbitrary code execution.
"""

import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

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

    def __init__(self):
        self._execution_history: List[Dict[str, Any]] = []
        self._recorded_pml_commands: List[str] = []
        self._lock = threading.RLock()

    @property
    def cmd(self):
        if cmd is None:
            raise PyMOLExecutionError("PyMOL is not available or could not be imported.")
        return cmd

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

        def _exec():
            self.cmd.show(rep, selection)
            return {"shown": rep, "selection": selection}

        res = self.run_safe(_exec)
        self.record_command(f"show {rep}, {selection}", "show_representation", {"representation": rep, "selection": selection}, res)
        return res

    def hide_representation(self, representation: str = "everything", selection: str = "all") -> Dict[str, Any]:
        """Hide representation for selection."""
        rep = representation.lower().strip()

        def _exec():
            self.cmd.hide(rep, selection)
            return {"hidden": rep, "selection": selection}

        res = self.run_safe(_exec)
        self.record_command(f"hide {rep}, {selection}", "hide_representation", {"representation": rep, "selection": selection}, res)
        return res

    def color_selection(self, color: str, selection: str = "all") -> Dict[str, Any]:
        """Apply color to selection."""
        c = color.strip()

        def _exec():
            if c.lower() == "bychain":
                self.cmd.util.color_chains(selection)
            elif c.lower() == "byelement" or c.lower() == "elem":
                self.cmd.util.cnc(selection)
            elif c.lower().startswith("rainbow"):
                self.cmd.spectrum("count", selection=selection)
            else:
                self.cmd.color(c, selection)
            return {"color": c, "selection": selection}

        res = self.run_safe(_exec)

        # Record valid PyMOL command according to color mode
        if c.lower() == "bychain":
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
        def _exec():
            self.cmd.zoom(selection, buffer=float(buffer))

        self.run_safe(_exec)
        self.record_command(f"zoom {selection}, buffer={buffer}", "zoom_selection", {"selection": selection, "buffer": buffer}, None)

    def orient(self, selection: str = "all") -> None:
        """Orient view along principal axes of selection."""
        def _exec():
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

        def _exec():
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

