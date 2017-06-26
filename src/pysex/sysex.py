#!/usr/bin/python

#   Copyright (C) 2017 dendrite.sysex@gmail.com
#
#   This library is free software; you can redistribute it and/or
#   modify it under the terms of the GNU Lesser General Public
#   License as published by the Free Software Foundation; either
#   version 2.1 of the License, or (at your option) any later version.
#
#   This library is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   Lesser General Public License for more details.
#
#   You should have received a copy of the GNU Lesser General Public
#   License along with this library; if not, write to the Free Software
#   Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301
#   USA


"""
    sysex.py - provide a top-level namespace to avoid circular deps
"""

__all__ = ['modref', 'MASTER', 'SysexLookupException']

# this maps names of Mods to corresponding instances
_MODS = {}
MASTER = 'master'

def modref(name):
    ''' return module by name
          can't auto-load without getting circular deps
          caller will need to catch KeyError and load
          mod.Mod() automatically registers self by name.
    '''
    try:
        return _MODS[name]
    except KeyError as exc:
        raise SysexLookupError(
            'function', 'Sysex.modref',
            'module not found', (name)) from exc

class SysexLookupError(Exception):
    ''' thrown when a lookup fails
    '''
    def __init__(self, objtype, name, problem, params=()):
        message = '%s %s: %s: %s' % (
            objtype, name, problem, params)
        super().__init__(message)
