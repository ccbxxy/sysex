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


''' mod.py
       module (file) processor
'''

# pylint: disable=bad-whitespace

import csv
import os
import copy
import collections
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
        try:
            path = os.environ['PYSEX_MODS']
        except KeyError:
            path = '.'

        if name.endswith('.csv'):
            fpath = name
            name = name[0:-4]
            parts = name.split(os.sep)
            name = '.'.join(parts)
        else:
            parts = name.split('.')
            fpath = os.sep.join(parts) + '.csv'

        fpath = os.sep.join([path, fpath])
        self._name = name
        self.loc = {
            'mod': name,
            'row': 0,
            'col': 0,
            'arg': 0
        }
        self.tabs = collections.OrderedDict()
        self._load(fpath)
        self.reader = None
        sysex.modreg(name, self)

    def _load(self, fpath):
        ''' load a module by reading its tables
        '''
        with open(fpath, newline='') as csvfile:
            self.reader = csv.reader(
                csvfile, delimiter=',', dialect='unix')
            meta = tab.TableMetaData()
            for line in self.reader:
                self.loc['row'] += 1

                if line[0].startswith('!END'):
                    return

                if line[0].startswith('#'):
                    continue

                if line[0].startswith('|'):
                    raise sysex.TableMetadataError(
                        'missing table header at %s' % self.loc)

                if line[0].startswith(']]'):
                    meta.desc = line[1:]
                    continue

                if line[0].startswith(']'):
                    if not line[0][1:]:
                        raise sysex.TableMetadataError(
                            'missing table name at %s' % self.loc)

                    if not line[1]:
                        raise sysex.TableMetadataError(
                            'missing table class at %s' % self.loc)

                    meta.name = line[0][1:]
                    meta.cls  = line[1]

                    if line[2] == 'None':
                        meta.over = None
                    else:
                        # table says it's an overlay for another.
                        #  capture contents as a Cell to allow
                        #  (]tab) and (!mod tab) expansions
                        cloc = copy.copy(self.loc)
                        cloc['cell'] = 2
                        meta.over = Cell(cloc, None, line[2])
                    continue

                if line[0].startswith('*'):
                    if not meta.cls:
                        raise sysex.TableMetadataError(
                            'missing table header at %s %s' % (
                                self.loc, line))

                    meta.cols = line[1:]
                    cls = meta.cls
                    table = cls(self, meta)
                    self.tabs[meta.name] = table
                    setattr(self, meta.name, tab)
                    meta = tab.TableMetaData()

    def marshall(self, dev, dump):
        ''' parse a dump into dev
        '''
        # pylint: disable=no-self-use
        pass

    def __str__(self):
        result = 'Mod Name: %s' % self._name
        for table in self.tabs:
            result += '\n%s' % self.tabs[table]
        return result

    def aswiki(self):
        ''' return a string representing a module in wiki markup
        '''
        result = '== Module: %s ==\n' % self._name
        for table in self.tabs:
            result += self.tabs[table].aswiki()
        return result
