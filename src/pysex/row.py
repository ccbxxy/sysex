#!/usr/bin/python3

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
        for nth, colid in tab.colids:
            loc = copy.copy(self.loc)
            loc['cell'] = nth+1
            self.put(colid, Cell(loc, self, data[nth]))

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


