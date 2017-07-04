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


''' table.py -
      generic table and specializations
'''

# pylint: disable=bad-whitespace

import copy
from pysex import algo
from pysex.mod import ModEndException
from pysex.row import Row
from pysex.sysex import SysexLookupError

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

    def _scanfor(self, tab, sigil, colid):
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
            if self._scanfor(tab, '@', colid):
                colid = tab.ident
            elif self._scanfor(tab, '*', colid):
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

            #! integrate syntax change for | markers
            if not line[1]:
                return

            self._addrow(Row(self.loc, self, line))

        if self._rows:
            return
        else:
            raise ModEndException

    def getrows(self, rowid, rqrow=None, colid=None, first=False):
        ''' return rows where rowid matches the key value
              filter by matches of rqrow in engine field
        '''
        rows = []
        if colid is None:
            if self.keyid:
                try:
                    return self.index[rowid]
                except KeyError:
                    pass

            colid = 'ident' if self.ident is None else self.ident

        rows = []
        for row in self._rows:
            if (getattr(row, colid)() == rowid and
                row.engine_match(rqrow)):
                if first:
                    return row
                else:
                    rows.append(row)

        if not rows:
            # dig deeper?
            parent = self.over()
            if parent:
                return parent.getrows(rowid, rqrow, colid, first)
            else:
                raise SysexLookupError(
                    'row', self.name,
                    'no values found',
                    (rowid, rqrow, colid))
        else:
            return rows

    def get1row(self, rowid, rqrow, colid=None):
        ''' get a unique row, qualified by rowid and membership of
             the rqrow in the engine field of the requested row
        '''
        rows = self.getrows(rowid, rqrow, colid)
        if len(rows) > 1:
            raise SysexLookupError(
                self, 'rows not unique',
                (rowid, rqrow, colid))

        return rows[0]

# pylint: disable=too-few-public-methods

## Table Subclasses, alphabetically
##

class CTRLTable(Table):
    ''' Table
    '''
    pass


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

    def sniff(self, data, vendor):
        ''' ask the vendor sniff if it knows what this is
            - data: MIDI byte buffer
            - vendor: vendor ID detected by Vendor.mma_lookup()
            - return: specific device table row detected or None
        '''
        return algo.sniff(vendor, self, data)


class DrumTable(Table):
    ''' Table
    '''
    pass


class FMTable(Table):
    ''' Provide a description of operator routing for FM algorithms
    '''
    def __init__(self, mod, name, over, meta=None):
        if not meta:
            meta = TableMetaData([
                ['Algorithm', '*ident'],
                ['Operators...', 'ops...']])

        super().__init__(mod, name, over, meta)

    def _flatten(self, ops):
        ''' convert cells to a simple array
        '''
        result = []
        for oper in ops:
            operval = oper()
            if isinstance(operval, Cell):
                result.append(self._flatten(operval))
            else:
                result.append(operval)

        return result

    def _distances(self, nop, oper):
        ''' for operator nop, return the maximum distance between this
              operator and operators that it modulates
        '''
        dist = set.set()
        if isinstance(oper, list):
            for anop in oper:
                dist.insert(nop - anop)
        else:
            dist.insert(nop-oper)

        return dist
    
    def pic(self, rowid):
        ''' render self on stream as text boxes
        '''
        
        #                  11111
        #        012345678901234
        box = [[' ┌───────────┐ ' ],
               [' │           │ ' ],
               [' │           │ ' ],
               [' │           │ ' ],
               [' └───────────┘ ' ] ]
        # modulator routing:
        #   mA to mB is 1: arrow to cell at position 11
        #                  arrow from cell at position 3
        #                  two rows tall
        #
        mod1 = [['┌──────┐'],
                ['▼      │'],
                ['       ┴']]

        #   mA to mB is 2: arrow to cell at position 10
        #                  arrow from cell at position 4
        #                  up to three rows tall
        #
        mod2 = [['┌─────X┐'],   # X: repeat prev char x 14
                ['│     X│'],
                ['▼     X│'], 
                ['      X┴']]

        #   mA to mB is 3: arrow to cell at position 9
        #                  arrow from cell at position 5
        #                  up to 4 rows tall
        #
        mod3 = [['┌────XX┐'],
                ['│    XX│'],
                ['▼    XX│'],
                ['     XX┴']]

        #   mA to mB is 4: arrow to cell at position 8
        #                  arrow from cell at position 6
        #                  up to 5 rows tall
        #
        mod4 = [['┌───XXX┐'],
                ['│   XXX│'],
                ['▼   XXX│'],
                ['    XXX┴']]

        #   mA to mB is 5: arrow to cell at position 8
        #                  arrow from cell at position 6
        #                  up to 6 rows tall
        #
        mod5 = [['┌──XXXX┐'],
                ['│  XXXX│'],
                ['▼  XXXX│'],
                ['   XXXX┴']]

        #   mA to mB is 0: (self modulating)
        #                  arrow from bottom cell 7
        #                  arrow to bottom cell 11
        #                  two rows tall
        mod0 = [['┬    '],
                ['│   ▲'],
                ['└───┘']]

        # Carrier: from bottom cell 5
        #
        car = [['┬' ],
               ['│' ],
               ['▼' ]]

        mods = [[mod0,  4,  7],
                [mod1, -2, 11],
                [mod2, -3, 10],
                [mod3, -4,  9],
                [mod4, -5,  8],
                [mod4, -6,  7],
                [car,   4,  5],
                [None,  2,  7]] # op number

        # this is sufficient for up to 6 operators
        #  FS1r owner can hack in wider boxes and arrows
        ops = self.get1row(rowid).route
        ops = self.flatten(ops)
        raster = []
        for oper in nops:
            for row in box:
                raster[row] += box[row]
            for row in car:
                #                    11111
                #          012345678901234
                raster += '               '
                
        # we now have a row of nops boxes
        #  how many rows of routing do we need?
        
        
class FXTable(Table):
    ''' Table
    '''
    pass

class HeaderTable(Table):
    ''' Header inside each device module
          will normally only be one line
    '''
    def __init__(self, mod, name, over, meta=None):
        meta = TableMetaData([
            [ 'Protocol', 'proto'    ],
            [ 'Layout',   'layout'   ],
            [ 'CC Map',   'cc_map'   ],
            [ 'NRPN Map', 'nrpn_map' ]])
        super().__init__(mod, name, over, meta)


class KBTable(Table):
    ''' Table
    '''
    pass

class ProtoTable(Table):
    ''' Device-specific Protocol
          yeah, these are a good candidate for a class decorator
    '''
    def __init__(self, mod, name, over, meta=None):
        meta = TableMetaData([
            [ 'Message Type', '*ident'   ],
            [ 'Message String', ':string' ]])
        super().__init__(self, mod, name, over, meta):


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
        row = self.get1row(rowid, rqrow)

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
        row = self.get1row(rowid, rqrow)

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


class SeqTable(Table):
    ''' Table
    '''
    pass


class TGTable(Table):
    ''' Table
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

    def midi(self, value):
        ''' sparse lookup with interpolation
            - value: floating value to be mapped to a MIDI byte
        '''
        # pylint: disable=no-member
        #   pylint doesn't know cells

        # find the rows between which the provided value falls
        dlast = flast = row = 0
        for row in self._rows:
            fdata = row.fdata()
            if fdata > value:
                break
            flast = fdata
            dlast = row.idata()

        # interpolate
        return int(
            round(row.scale() * (value - flast) + dlast, 0))


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
        for row in self._rows:
            if row.mma_id()[0] == 0x00:
                setattr(row, '_idlen', 1)
            else:
                setattr(row, '_idlen', 3)

    def mma_lookup(self, data):
        ''' return the row matching the first 1 or 3 bytes in
              the data stream
        '''
        idlen = 1 if data[0] == 0x00 else 3
        row = self.get1row(data[0:idlen], rqrow=None, colid='mma_id')
        self.eat_id(data, idlen)
        return row

    def eat_id(self, data, idlen=None):
        ''' consume the ID from the data buffer
        '''
        # pylint: disable=no-self-use
        #  SCOPE
        if idlen is None:
            idlen = 1 if data[0] == 0x00 else 3
        del data[0:idlen]
        return idlen



# pylint: enable=too-few-public-methods

CLASSES = {
    # vendors.csv tables
    #   one per system
    'VendorTable': VendorTable,

    # <vendor>.devices.csv tables
    #   one per vendor
    'DeviceTable': DeviceTable,

    # devtype.csv tables
    #   one each per system
    'CTRLTable':  CTRLTable,
    'DrumTable':  DrumTable,
    'FXTable':    FXTable,
    'IOTable':    IOTable,
    'KBTable':    KBTable,
    'TGTable':    TGTable,
    'SeqTable':   SeqTable

    # <device>.csv tables
    #   as needed per device
    'ChoiceTable': ChoiceTable,
    'FMTable':     FMTable,
    'HeaderTable': HeaderTable,
    'MemoryMap':   MemoryMap,
    'ParamTable':  ParamTable,
    'ProtoTable':  ProtoTable,
    'ValueTable':  ValueTable
}
