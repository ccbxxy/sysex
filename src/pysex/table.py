#!/usr/bin/python3

''' table.py -
      generic table and specializations
'''

# pylint: disable=bad-whitespace

from pysex import algo

class Row(object):
    ''' represents a table row
    '''
    def __init__(self, data, tab):
        ''' create a row
            - data: list of Cell
            - tab:  parent table of the cell
        '''
        self._tab = tab
        self._keycell = None
        for colid in tab.colids:
            self.put(colid, data.pop(0))

        if tab.key:
            self._keycell = self.get(tab.key)

    @property
    def keycell(self):
        return self._keycell

    @property
    def tab(self):
        return self._tab
    
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


class Table(object):
    ''' base class for our tables
    '''
    _tables = {}
    _globals = {}

    @classmethod
    def get(cls, name):
        return cls._tables[name]

    @classmethod
    def factory(cls, fp, loc, line):
        classes = {
            'Vendors':     VendorTable,
            'Devices':     DeviceTable,
            'Keyboard':    KeyboardTable,
            'Controller':  ControllerTable,
            'ToneGen':     ToneGenTable,
            'Drum':        DrumTable,
            'Seq':         SeqTable,
            'HeaderTable': HeaderTable
            'ProtoTable':  ProtoTable,
            'MemoryMap':   MemMapTable,
            'ChoiceTable': ChoiceTable,
            'ParamTable':  ParamTable,
            'ValueTable':  ValueTable
        }
        parts = line.split(',')
        subclass = classes[parts[1]]
        tab = subclass(parts[1][1:], None, None)

        while True:
            line = fp.readline()
            if not line:
                return tab
            loc[1] += 1

            parts = line.split(',')
            if not parts[1]:
                return tab
            
            tab.addrow(
                Row( 
                    [ cell.Cell.factory(loc + [colno], part)
                      for colno, part in enumerate(parts) ]))
            
    def __init__(self, name, meta, colids):
        '''
            - meta: metadata values
            - cols: column descriptors (names)
        '''
        self.name = name
        self.meta = meta
        self.key = None
        self._index = {}
        self.colids = self._unique(
            [self._keyscan(colid) for colid in colids])
        self._rows = []
        Table._tables[name] = self
    
    def _keyscan(self, colid):
        if colid.startswith('*'):
            colid = colid[1:]
            if self.key:
                raise KeyError(
                    'Table %s: %s and %s cannot both be keys' % (
                        self.name, self.key, colid))
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
                        self.name, colid))

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
                        self.name, keyval, self.key))
            self._index[keyval] = newrow

        self._rows.append(newrow)

    def value(self, var, arg):
        method = var.pop(0)
        return method(self, var, arg)

    def engine(self, rqrow):
        if engine:
            return engine.split('.')[0]
        else:
            return engine

    def row_select(self, rowid, rqrow):
        rows = [ row  for row in self._rows
                 if row.ident == rowid ]

        if not rows:
            return rows

        if not engine:
            return rows

        result = []
        for row in rows:
            rengine = row.engine.value(self)
            if not rengine or not engine:
                # either caller or table needs no filter
                result.append(row)
            elif engine in rengine:
                result.append(row)

        return result

    def row_unique(self, rowid, rqrow):
        ''' select rows by rowid
              return the first where engine matches rqrow
        '''
        rows = self.row_select(rowid, self.engine(rqrow))
        if not rows:
            raise ValueError(
                '%s: no param for ident=%s,engine=%s' % (
                    self.name, rowid, engine))

        if len(rows) > 1:
            raise ValueError(
                '%s: non-unique param: ident=%s,engine=%s' % (
                    self.name, rowid, ))

        return rows.pop()


class MemoryMap(Table):
    ''' table that maps a block of device addresses to properties
         each address can map to:
           a ParamTable row characterizing the value at that address
           a ChoiceTable providing a large (>5) number of value choices
           a MemoryMap with finer-grained mapping of part of the addr space
    '''
    def __init__(self, name, meta, colids):
        colinfo = [
            [ 'Block ID', 'ident' ],
            [ 'Block Name', 'name' ],
            [ 'Address', 'addr' ],
            [ 'Entry Count', 'count' ],
            [ 'Entry Stride', 'stride' ],
            [ 'Sub Map', 'submap' ],
            [ '-', None ],
            [ '-', None ],
            [ '-', None ],
            [ 'Choice/Param Table', 'params' ]
        ]
        super(MemoryMap, self).__init__(
            name,
            [ent[0] for ent in colinfo],
            [ent[1] for ent in colinfo])


class ChoiceTable(Table):
    ''' Table providing a way to select from groups of paramters
    '''
    def __init__(self, name, meta, colids):
        colinfo = [
            [ 'Ident',       'ident' ],
            [ 'Name',        'name' ],
            [ 'Midi Value',  'data' ],
            [ 'Param Table', 'table' ]
        ]
        super(ChoiceTable, self).__init__(
            name,
            [ent[0] for ent in colinfo],
            [ent[1] for ent in colinfo])


class ParamTable(Table):
    ''' Table of Parameter Descriptions
    '''
    #! work out behringer and alesis bitfielding

    def __init__(self, name, meta, colids):
        colinfo = [
            [ 'Ident',      'ident' ],
            [ 'Engine',     'engine' ],
            [ 'Param',      'param' ],
            [ 'Byte Count', 'bytec' ],
            [ 'Range',      'range' ],
            [ 'Rendering',  'render' ],
            [ 'Scaling',    'scale' ],
            [ 'Val Shift',  'shift' ],
            [ 'Units',      'units' ]
        ]
        super(ParamTable, self).__init__(
            name,
            [ent[0] for ent in colinfo],
            [ent[1] for ent in colinfo])

    def value(self, rowid, rqrow, midi):
        ''' convert a MIDI byte to a value
                shift, then scale
        '''
        row = self.row_unique(rowid, rqrow)
        val = algo.ALGOMAP[row.render].value(
            midi, row.bytec.value(self))

        val = row.shift.value(self, val)

        # if scale is (* val), scaling is done in MulCell
        # if scale is (]tab), scaling is done in ValueTable
        return row.scale.value(self, val)

    def midi(self, rowid, rqrow, val):
        ''' convert value to a MIDI bytes
        '''
        row = self.row_unique(rowid, rqrow)

        # unscale
        scale = row.scale.value(self)
        val = val / scale

        # unshift
        shift = row.shift.value(self)
        val =- shift
        return algo.Render.factory(
            row.render.value(self)).midi(val, row.bytec.value(self))

    def vrange(self, rowid):
        ''' return the endpoints of the scaled range values
        '''
        pass


class ValueTable(Table):
    ''' table that maps MIDI byte values to float values
          used by many vendors in effects parameter translations
    '''
    def __init__(self, name, meta, colids):
        colinfo = [
            [ 'Data Value', 'idata' ],
            [ 'Mapped Value', 'fdata' ],
            [ 'Scaling', 'scale' ],
            [ 'Rounding', 'rounding' ]
        ]
        super(ValueTable, self).__init__(
            name,
            [ent[0] for ent in colinfo],
            [ent[1] for ent in colinfo])

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
