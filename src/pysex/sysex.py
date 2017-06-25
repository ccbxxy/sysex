#!/usr/bin/python
"""
    sysex.py - provide a top-level namespace to avoid circular deps
"""

# pylint: disable=invalid-name

__all__ = ['mods']

# this maps names of Mods to corresponding instances
mods = {}
