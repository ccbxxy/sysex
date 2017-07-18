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
import collections
from psysex import sysex
from psysex import tab
from psysex import cell

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
            path = os.environ['PSYSEX_MODS']
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
        self._tabs = collections.OrderedDict()
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
                try:
                    col_a, col_b, col_c = line[0:3]
                except ValueError as exc:
                    raise sysex.TableMetadataError(
                        '%s: row has fewer than 3 columns' % (
                            self.loc)) from exc

                if col_a.startswith('!END'):
                    return

                if col_a.startswith('#'):
                    continue

                if col_a.startswith('|'):
                    raise sysex.TableMetadataError(
                        'missing table header at %s' % self.loc)

                if col_a.startswith(']]'):
                    meta.desc = line[1:]
                    continue

                if col_a.startswith(']'):
                    if not col_a[1:]:
                        raise sysex.TableMetadataError(
                            '%s: missing table name' % self.loc)

                    if not col_b:
                        raise sysex.TableMetadataError(
                            '%s: missing table class' % self.loc)

                    if not col_c:
                        raise sysex.TableMetadataError(
                            '%s: missing table overlay' % self.loc)

                    meta.name = col_a[1:]
                    meta.cls  = col_b

                    cloc = self.loc.copy()
                    cloc['cell'] = 2
                    meta.over = cell.factory(cloc, None, col_c)
                    continue

                if col_a.startswith('*'):
                    if not meta.cls:
                        raise sysex.TableMetadataError(
                            '%s: "*" but no table header' % self.loc)

                    meta.cols = line[1:]
                    cls = meta.cls
                    table = cls(self, meta)
                    self._tabs[meta.name] = table
                    setattr(self, meta.name, tab)
                    meta = tab.TableMetaData()

    def marshall(self, dev, dump):
        ''' parse a dump into dev
        '''
        # pylint: disable=no-self-use
        pass

    def aswiki(self):
        ''' return a string representing a module in wiki markup
        '''
        result = '== Module: %s ==\n' % self._name
        for table in self._tabs:
            result += self[table].aswiki()
        return result

    def __getitem__(self, tabname):
        return self._tabs[tabname]

    def __str__(self):
        result = 'Mod Name: %s' % self._name
        for table in self._tabs:
            result += '\n%s' % self[table]
        return result

