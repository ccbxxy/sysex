#!/usr/bin/env python3

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


''' syxmod.py
       module (file) processor
'''

# pylint: disable=bad-whitespace

import csv
import os
import copy
from pysex import sysex
from pysex import tab
from pysex.cell import Cell

__all__ = ['Mod']

class Mod(object):
    ''' Internal respresentation of a sysex CSV module
    '''
    # pylint: disable=too-few-public-methods
    def __init__(self, name):
        ''' ctor
            - name: dotted path to module
        '''
        if name.endswith('.csv'):
            fpath = name
            name = name[0:-4]
            parts = name.split(os.sep)
            name = '.'.join(parts)
        else:
            parts = name.split('.')
            fpath = os.sep.join(parts) + '.csv'

        self._name = name
        self.loc = {
            'name': name,
            'row':  0,
            'cell': 0,
            'arg':  0
        }
        self.tabs = {}
        self._load(fpath)
        self.reader = None
        sysex.modreg(name, self)

    def _load(self, fpath):
        with open(fpath, newline='') as csvfile:
            self.reader = csv.reader(
                csvfile, fieldnames='', delimiter=',', dialect='unix')
            for line in self.reader:
                self.loc['row'] += 1

                if line[0].startswith[']']:
                    name = line[0][1:]
                    _class = line[1]
                    if line[2]:
                        # table says it's an overlay for another.
                        #  capture contents as a Cell to allow
                        #  (]tab) and (!mod tab) expansions
                        cloc = copy.copy(self.loc)
                        cloc['cell'] = 2
                        over = Cell(cloc, None, line[2])
                    else:
                        over = None
                try:
                    table = tab.CLASSES[_class](self, name, over)
                except sysex.ModEndException:
                    return

            self.tabs[table.name] = tab
            setattr(self, table.name, tab)

