"""
Runtime PyMOL version discovery for provenance and reproducibility records.
"""

from typing import Any


def get_pymol_version() -> str:
    """
    Return the running PyMOL version as a string, or "unknown" when unavailable.

    PyMOL's ``cmd.get_version()`` returns a tuple whose first item is the
    human-readable version (e.g. ``"3.1.0"``); older/stub builds may return a
    string or nothing at all.
    """
    try:
        from pymol import cmd

        version: Any = cmd.get_version()
        if isinstance(version, (tuple, list)):
            version = version[0] if version else None
        if version:
            return str(version)
    except Exception:
        pass
    return "unknown"
