#!/usr/bin/python3

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


''' row.py - row of cells in our data model
'''

import copy
from pysex.cell import Cell

class Row(object):
    ''' represents a table row
    '''
    def __init__(self, loc, tab, data):
        ''' create a row
            - loc:  [mod, line]
            - tab:  parent table of the cell
            - data: list of Cell
        '''
        def nope(arg):
            ''' callable None, no key field in this table
            '''
            # pylint: disable=unused-argument
            raise KeyError('%s: no key available' % loc)

        self.loc = loc
        self.tab = tab
        self._keyed = nope

        cloc = copy.copy(self.loc)
        for nth, colid in tab.colids:
            if colid.startswith('-'):
                # allow horizontal padding
                continue
            
            cloc['cell'] = nth+1
            if colid.endswith('...'):
                # syntactic sugar.
                #   convert remaining cols to a 'x;y;z;t' cell
                colid = colid[0:-3]
                subcells = []
                scloc = copy.copy(cloc)
                for ith, col in enumerate(data[nth:]):
                    if not col:
                        break
                    scloc['arg'] = ith
                    subcells.append(Cell(scloc, self, col))
                self.put(colid, Cell(cloc, self, subcells))
                break
                
            self.put(colid, Cell(cloc, self, data[nth]))

        if tab.key:
            self._keyed = self.get(tab.key)

    @property
    def key(self):
        ''' return the value of the key cell
        '''
        return self.rkey()

    @property
    def rkey(self):
        ''' return the key cell
        '''
        return self._keyed

    def get(self, colid):
        ''' return a specific cell
            - colid: cell identifier
        '''
        return getattr(self, colid)

    def put(self, colid, acell):
        ''' replace the cell at colid
            - colid: item in row to update
            - acell: new cell
        '''
        #! don't forget to key check updates to unique cols
        setattr(self, colid, acell)
        return acell

    def engine_match(self, rqrow):
        ''' true if rqrow is in the engine field
        '''
        # pylint: disable=no-member
        #   not happy with setattr shenanigans

        if self.engine is None:
            return True

        rqe = rqrow.split('.')[0]
        return rqe in self.engine()
