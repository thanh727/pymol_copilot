"""
Native PyMOL plugin entry point and lifecycle manager.
Integrates with PyMOL's Plugins menu and command line interface.
"""

from typing import Optional

try:
    from pymol import Qt, cmd
    QtWidgets = Qt.QtWidgets
except ImportError:
    cmd = None
    QtWidgets = None

from .ui.chat_panel import CopilotDialog

_copilot_window: Optional[CopilotDialog] = None


def get_pymol_parent_window():
    """Attempt to find PyMOL's main Qt window to set as parent."""
    try:
        from pmg_qt import pymol_qt_gui
        if hasattr(pymol_qt_gui, "window") and pymol_qt_gui.window:
            return pymol_qt_gui.window
    except Exception:
        pass

    if QtWidgets:
        app = QtWidgets.QApplication.instance()
        if app:
            for widget in app.topLevelWidgets():
                if isinstance(widget, QtWidgets.QMainWindow):
                    return widget
            return app.activeWindow()
    return None


def show_copilot_window():
    """
    Open or bring to front the PyMOL AI Copilot window.
    Ensures safe, single-instance execution without crashes or duplicate dialogs.
    """
    global _copilot_window

    parent = get_pymol_parent_window()

    if _copilot_window is None:
        _copilot_window = CopilotDialog.get_instance(parent)

    # Bring window to front
    _copilot_window.show()
    _copilot_window.raise_()
    _copilot_window.activateWindow()
    _copilot_window.refresh_structure_context()
    return _copilot_window


def __init_plugin__(app=None):
    """
    Official PyMOL plugin entry point called during PyMOL startup or manual loading.
    """
    try:
        from pymol.plugins import addmenuitemqt
        addmenuitemqt("AI Copilot", show_copilot_window)
    except Exception:
        try:
            from pymol.plugins import addmenuitem
            addmenuitem("AI Copilot", show_copilot_window)
        except Exception as e:
            print(f"[PyMOL AI Copilot] Warning: Could not register menu item: {e}")

    # Extend PyMOL CLI with 'ai_copilot' command
    if cmd:
        cmd.extend("ai_copilot", show_copilot_window)

    print("[PyMOL AI Copilot] Plugin loaded successfully. Launch from 'Plugin -> AI Copilot' or type 'ai_copilot'.")

