#!/usr/bin/env python3
"""
Installation and management script for PyMOL AI Copilot.
Registers the plugin in PyMOL's user startup folder and safely updates
~/.pymolpluginsrc.py without overwriting existing plugin configuration.
"""

import argparse
import sys

from pymol_ai_copilot.installer import install_plugin, uninstall_plugin


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="PyMOL AI Copilot Installer")
    parser.add_argument("--uninstall", action="store_true", help="Uninstall the plugin")
    args = parser.parse_args(argv)

    ok = uninstall_plugin() if args.uninstall else install_plugin()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
