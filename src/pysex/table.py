#!/usr/bin/python3

''' table.py -
      generic table and specializations
'''

# pylint: disable=bad-whitespace

from pysex import cell

class Row(object):
    ''' represents a table row
    '''
    def __init__(self, data, tab):
        ''' create a row
            - data: list of Cell
            - tab:  parent table of the cell
        '''
        self._table = tab
        self._key = tab.key
        for colid in tab.colids:
            self.put(colid, data.pop(0))

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

    def value(self, context, colid, newval=(None, None)):
        ''' get/set the value of a specific cell
            - context: symbolic context for Cell.value()
            - colid: item in row to evaluate
            - newval=(None, None): loc, value a new cell
                value will be parsed... may include substitutions
            - return: the new value
        '''
        loc, val = newval
        if loc:
            acell = cell.Cell.factory(loc, val)
            setattr(self, colid, acell)
            return acell.value(context)
        else:
            return getattr(self, colid).value(context)


class Table(object):
    ''' base class for our tables
    '''
    def __init__(self, name, meta, colids):
        '''
            - meta: metadata values
            - cols: column descriptors (names)
        '''
        self.key = None
        self._index = {}
        self._name = name
        self._meta = meta
        self.colids = self._unique(
            [self._getkey(colid) for colid in colids])
        self._rows = []

    def _getkey(self, colid):
        if colid.startswith('*'):
            colid = colid[1:]
            if self.key:
                raise KeyError(
                    'Table %s: %s and %s cannot both be keys' % (
                        self._name, self.key, colid))
            self.key = colid
        return colid

    def _unique(self, colids):
        for i in range(0, len(colids)):
            colid = colids[i]
            if colid == '...' or colid == '-':
                continue

            if colid in colids[i+1:]:
                raise KeyError(
                    'Table %s: duplicate col id: %s' % (
                        self._name, colid))

        return colids

    def addrow(self, row):
        ''' add a row
            - row: an array of Cell
        '''
        newrow = Row(row, self)
        if self.key:
            keyval = newrow.get(self.key)
            if keyval in self._index:
                raise KeyError(
                    'Table %s: duplicate value %s for key %s' % (
                        self._name, keyval, self.key))
            self._index[keyval] = newrow

        self._rows.append(newrow)


class MemoryMap(Table):
    ''' table that maps a block of device addresses to properties
         each address can map to:
           a ParamTable row characterizing the value at that address
           a ChoiceTable providing a large (>5) number of value choices
           a MemoryMap with finer-grained mapping of part of the addr space
    '''
    def __init__(self, name, meta, colids):
        meta = [
            'Block Mnemonic',
            'Block Name',
            'Address',
            'Entry Count',
            'Entry Stride',
            'Sub Map',
            '-',
            '-',
            '-',
            'Choice/Param Table'
        ]
        colids = [
            'id',
            'name',
            'addr',
            'count',
            'stride',
            'memmap'
            '-', '-', '-',
            'values'
        ]
        super(MemoryMap, self).__init__(name, meta, colids)


class ChoiceTable(Table):
    ''' Table providing a way to select from groups of paramters
    '''
    pass

class ValueTable(Table):
    ''' table that maps MIDI byte values to float values
          used by many vendors in effects parameter translations
    '''
    def __init__(self, name, meta, colids):
        meta = [
            'Data Value',
            'Output Value',
            'Scaling',
            'Rounding'
        ]
        colids = [
            'idata',
            'fdata',
            'scale',
            'rounding'
        ]
        super(ValueTable, self).__init__(name, meta, colids)

    def value(self, context, data):
        ''' sparse lookup with interpolation
            - context: symbol environment
            - data: single MIDI data byte
        '''
        # pylint: disable=no-member
        #   pylint doesn't know cells

        # find the rows between which the midi byte falls
        ilast = flast = row = 0
        for row in self._rows:
            idata = row.idata.value(context)
            if idata > data:
                break
            ilast = idata
            flast = row.fdata.value(context)

        # interpolate
        return round( row.scale.value(context) * (data - ilast) + flast,
                      row.rounding.value(context))

    def midi(self, context, value):
        ''' sparse lookup with interpolation
            - context: symbol environment
            - value: floating value to be mapped to a MIDI byte
        '''
        # pylint: disable=no-member
        #   pylint doesn't know cells

        # find the rows between which the provided value falls
        dlast = flast = row = 0
        for row in self._rows:
            fdata = row.fdata.value(context)
            if fdata > value:
                break
            flast = fdata
            dlast = row.idata.value(context)

        # interpolate
        return int(
            round(row.scale.value(context) * (value - flast) + dlast, 0))
