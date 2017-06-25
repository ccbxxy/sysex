#!/usr/bin/python3

''' table.py -
      generic table and specializations
'''

# pylint: disable=bad-whitespace

import copy
from pysex import algo
from pysex.mod import ModEndException
from pysex.row import Row

__all__ = ['Table', 'CLASSES']



class TableMetaData(object):
    ''' container for table descriptions and column IDs
    '''
    def __init__(self, colinfo=None):
        self.humids, self.colids = None, None
        if colinfo:
            self.humids = [elt[0] for elt in colinfo]
            self.colids = [elt[1] for elt in colinfo]

    def _put(self, tab, sigil, filt, line):
        props = {
            ']]': 'humids',
            '*':  'colids'
        }
        if line[0].startswith(sigil):
            prop = props[sigil]
            if not getattr(self, prop):
                setattr(self, prop, filt(tab, line[1:]))
            return True
        else:
            return False

    def puthumids(self, tab, line):
        ''' setter.  never overrides existing colids
            - tab: table under construction
            - line: line from the table
            - return: True if was colids line, False otherwise
        '''
        return self._put(tab, ']]', lambda t, x: x, line)

    def putcolids(self, tab, line):
        ''' setter.  never overrides existing colids
            - tab: table under construction
            - line: line from the table
            - return: True if was colids line, False otherwise
        '''
        return self._put(tab, '*', self.scan, line)

    def scanfor(self, tab, sigil, colid):
        ''' process '@', '*'
            - sigil: one of '@', '*'
            - prop:  one of 'ident', 'keyid'
            - tab:   table under contruction
            - colid: colid to process
        '''
        # pylint: disable=no-self-use
        #  Here for scope
        props = {
            '@': 'ident',
            '*': 'keyid'
        }

        if colid.startswith(sigil):
            # non-unique identity row
            colid = colid[1:]
            prop = props[sigil]
            propval = getattr(tab, prop)
            if propval:
                raise ValueError(
                    'Table %s: %s and %s cannot both be %s cols' % (
                        tab.name, propval, colid, prop))
            setattr(tab, prop, colid)

    def scan(self, tab, line):
        ''' process @colid, *colid semantics
              enforce colid uniqueness
            - tab: table under construction
            - line: array of text tokens from input
        '''
        colids = []
        for num, colid in enumerate(line):
            if self.scanfor(tab, '@', colid):
                colid = tab.ident
            elif self.scanfor(tab, '*', colid):
                colid = tab.keyid
            colids.append(colid)
            if colid in colids[0:num]:
                # colids must be unique
                raise ValueError(
                    'Table %s: duplicate col id: %s' % (
                        tab.name, colid))
        return colids


class Table(object):
    ''' base class for our tables
    '''
    # pylint: disable=too-few-public-methods,too-many-instance-attributes
    def __init__(self, mod, name, over, meta=None):
        '''
        '''
        self.mod = mod
        self.name = name
        self.over = over
        self.loc = copy.copy(mod.loc)
        self.keyid = None
        self.ident = None
        self.index = {}
        self._rows = []

        if meta:
            meta.scan(self, meta.colids)
            self.meta = meta
        else:
            self.meta = TableMetaData()

        self._load(mod.reader)

    def _addrow(self, row):
        ''' add a row
            - row: an array of Cell
        '''
        if self.keyid in self.index:
            raise KeyError(
                'Table %s: duplicate value %s for key %s' % (
                    self.name, row.key, self.keyid))
        self.index[row.rkey] = row
        self._rows.append(row)

    def _load(self, reader):
        ''' read a table from csv.reader
        '''
        for line in reader:
            self.loc['row'] += 1

            if self.meta.puthumids(self, line):
                continue

            if self.meta.putcolids(self, line):
                continue

            if not line[1]:
                return

            self._addrow(Row(self.loc, self, line))

        if self._rows:
            return
        else:
            raise ModEndException

    def _get_erows(self, rows, rqrow):
        engine = rqrow.split('.')[0]
        result = []
        for row in rows:
            try:
                rengine = row.engine.value(self)
            except AttributeError:
                # row does not have an 'engine'
                rengine = None

            if not rengine:
                # no engine filter on row
                result.append(row)
            elif engine in rengine:
                result.append(row)

        return result

    def _get_orows(self, rowid, rqrow):
        if self.over:
            return self.over.value().getrow(rowid, rqrow)

    def getrow(self, rowid, rqrow=None):
        ''' return rows where rowid matches the key value
              filter by matches of rqrow in engine field
        '''
        rows = []
        if self.keyid:
            try:
                return self.index[rowid]
            except KeyError:
                pass
        else:
            rows = [ row
                     for row in self._rows
                     if row.ident.value() == rowid ]

        if not rows:
            # this table may overlay another
            return self._get_orows(rowid, rqrow)

        if rqrow:
            return self._get_erows(rows, rqrow)
        else:
            return rows

    def _get_arow(self, rowid, rqrow):
        ''' get a unique row, qualified by rowid and membership of
             the rqrow in the engine field of the requested row
        '''
        rows = self.getrow(rowid, rqrow)
        if len(rows) > 1:
            raise ValueError(
                '%s: too may rows selected with rowid, rqrow: %s, %s',
                (self.loc, rowid, rqrow))
        return rows[0]

# pylint: disable=too-few-public-methods

class VendorTable(Table):
    ''' Table
    '''
    def __init__(self, mod, name, over, meta=None):
        meta = TableMetaData([
            [ 'Ident',        '*ident' ],
            [ 'Company Name', 'name'   ],
            [ 'MMA SYSEX ID', 'mma_id' ]
        ])
        super().__init__(mod, name, over, meta)

class DeviceTable(Table):
    ''' Table
    '''
    def __init__(self, mod, name, over, meta=None):
        meta = TableMetaData([
            [ 'Device Name',   '*ident'   ],
            [ 'Vendor ID',     'vendor'   ],
            [ 'IDRQ Response', 'idrq'     ],
            [ 'Protocol ID',   'proto_id' ],
            [ 'Device Type',   'type'     ]])

        super().__init__(mod, name, over, meta)


class KBTable(Table):
    ''' Table
    '''
    pass

class TGTable(Table):
    ''' Table
    '''
    pass

class CTRLTable(Table):
    ''' Table
    '''
    pass

class DrumTable(Table):
    ''' Table
    '''
    pass

class FXTable(Table):
    ''' Table
    '''
    pass

class SeqTable(Table):
    ''' Table
    '''
    pass

class HeaderTable(Table):
    ''' Table
    '''
    pass

class ProtoTable(Table):
    ''' Table
    '''
    pass


class MemoryMap(Table):
    ''' table that maps a block of device addresses to properties
         each address can map to:
           a ParamTable row characterizing the value at that address
           a ChoiceTable providing a large (>5) number of value choices
           a MemoryMap with finer-grained mapping of part of the addr space
    '''
    def __init__(self, mod, name, over, meta=None):
        meta = TableMetaData([
            [ 'Block ID',     'ident'  ],
            [ 'Block Name',   'name'   ],
            [ 'Address',      'addr'   ],
            [ 'Entry Count',  'count'  ],
            [ 'Entry Stride', 'stride' ],
            [ 'Sub Map',      'submap' ],
            [ '-',            None     ],
            [ '-',            None     ],
            [ '-',            None     ],
            [ 'Rendering',    'params' ]])

        super().__init__(mod, name, over, meta)


class ChoiceTable(Table):
    ''' Table providing a way to select from groups of paramters
    '''
    def __init__(self, mod, name, over):
        meta = TableMetaData([
            [ 'Ident',       'ident' ],
            [ 'Name',        'name'  ],
            [ 'Midi Value',  'data'  ],
            [ 'Param Table', 'table' ]])

        super().__init__(mod, name, over, meta)


class ParamTable(Table):
    ''' Table of Parameter Descriptions
    '''
    #! work out behringer and alesis bitfielding

    def __init__(self, mod, name, over, meta=None):
        meta = TableMetaData([
            [ 'Ident',      'ident'  ],
            [ 'Engine',     'engine' ],
            [ 'Param',      'param'  ],
            [ 'Byte Count', 'bytec'  ],
            [ 'Range',      'range'  ],
            [ 'Rendering',  'render' ],
            [ 'Scaling',    'scale'  ],
            [ 'Val Shift',  'shift'  ],
            [ 'Units',      'units'  ]])
        super().__init__(mod, name, over, meta)

    def value(self, rowid, rqrow, midi):
        ''' convert a MIDI byte to a value
              the row provides semantics for interpreting the midi
              byte or bytes
        '''
        # get the row
        row = self._get_arow(rowid, rqrow)

        # if scale is (* val), scaling is done in MulCell
        # if scale is (]tab), scaling is done in ValueTable

        # remember: scale and shift are cells in the current row
        #  and that () gets the value of a cell
        #
        return row.scale(
            row.shift(
                algo.tovalue(row.render(), midi)))

    def midi(self, rowid, rqrow, val):
        ''' convert value to a MIDI bytes
        '''
        row = self._get_arow(rowid, rqrow)

        # unscale
        scale = row.scale()
        val = val / scale

        # unshift
        shift = row.shift()
        val =- shift
        return algo.tomidi(row.render(), val, row.bytec())

    def vrange(self, rowid):
        ''' return the endpoints of the scaled range values
        '''
        pass


class ValueTable(Table):
    ''' table that maps MIDI byte values to float values
          used by many vendors in effects parameter translations
    '''
    def __init__(self, mod, name, over):
        meta = TableMetaData([
            [ 'Data Value',   'idata' ],
            [ 'Mapped Value', 'fdata' ],
            [ 'Scaling',      'scale' ],
            [ 'Precision',    'prec'  ]])

        super().__init__(mod, name, over, meta)

    def value(self, data):
        ''' sparse lookup with interpolation
            - context: symbol environment
            - data: single MIDI data byte
        '''
        # pylint: disable=no-member
        #   pylint doesn't know cells

        # find the rows between which the midi byte falls
        ilast = flast = row = 0
        for row in self._rows:
            idata = row.idata()
            if idata > data:
                break
            ilast = idata
            flast = row.fdata()

        # interpolate
        return round(row.scale() * (data - ilast) + flast, row.prec())

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

# pylint: enable=too-few-public-methods

CLASSES = {
    # master.csv tables
    'Vendors':     VendorTable,
    'Devices':     DeviceTable,
    'Keyboard':    KBTable,
    'Controller':  CTRLTable,
    'TG':          TGTable,
    'Drum':        DrumTable,
    'Seq':         SeqTable,

    # device module tables
    'HeaderTable': HeaderTable,
    'ProtoTable':  ProtoTable,
    'MemoryMap':   MemoryMap,
    'ChoiceTable': ChoiceTable,
    'ParamTable':  ParamTable,
    'ValueTable':  ValueTable
}
