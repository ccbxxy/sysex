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

from psysex import algo
from psysex import row
from psysex.sysex import SysexLookupError

__all__ = ['Table', 'TableMetaData', 'CLASSES']



class TableMetaData(object):
    ''' container for table descriptions and column IDs
    '''
    def __init__(self):
        self.cols = None
        self.desc = None
        self._cls  = None
        self.name = None
        self.over = None
        self.tab = None

    @property
    def cls(self):
        ''' return the class I'm pimping for
        '''
        return self._cls

    @cls.setter
    def cls(self, name):
        ''' bind this instance to a table class
        '''
        self._cls = CLASSES[name]

    def _scanfor(self, tab, sigil, colid):
        ''' process '@', '*'
            - sigil: one of '@', '*'
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
            propval = tab[prop]
            if propval:
                raise ValueError(
                    '%s: %s and %s cannot both be %s cols' % (
                        self.tab.mod.loc, propval, colid, prop))
            tab[prop] = colid
            return True
        return False

    def bind(self, tab):
        ''' process @colid, *colid semantics & enforce colid uniqueness
            - tab: table under construction
        '''
        colids = []
        self.tab = tab
        for num, colid in enumerate(self.cols):
            if not colid or colid.startswith('#'):
                break           # trim ,,,
            if colid.startswith('-'):
                # padding
                colids.append('_PAD')
                continue

            if self._scanfor(tab, '@', colid):
                colid = colid[1:]
            elif self._scanfor(tab, '*', colid):
                colid = colid[1:]
            elif colid.endswith('...'):
                colid = colid[0:-3]
                tab.elipse = colid
            if colid in colids[0:num]:
                # colids must be unique
                raise ValueError(
                    'Table %s: duplicate col id: %s at %s' % (
                        self.name, colid, tab.loc))
            colids.append(colid)

        self.cols = colids

    def __str__(self):
        return self.name


class Table(object):
    ''' base class for our tables
    '''
    # pylint: disable=too-few-public-methods,too-many-instance-attributes
    def __init__(self, mod, meta):
        '''
        '''
        self.mod = mod
        self.meta = meta
        self.keyid = None
        self.ident = None
        self.elipse = None
        self.index = {}
        self._rows = []
        self.meta.bind(self)
        self._load(mod.reader)

    def _addrow(self, arow):
        ''' add row
            - arow: an array of Cell
        '''
        if self.keyid in self.index:
            raise KeyError(
                '%s: table %s: duplicate value %s for key %s' % (
                    self.mod.loc, self.meta.name, arow.key, self.keyid))
        self.index[arow.rkey] = arow
        self._rows.append(arow)

    def _load(self, reader):
        ''' read a table from csv.reader
        '''
        for line in reader:
            self.mod.loc['row'] += 1

            if line[0].startswith('#'):
                continue

            if not line[0].startswith('|'):
                return

            self._addrow(row.Row(self.mod.loc, self, line[1:]))

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
        for arow in self._rows:
            if arow[colid]() == rowid and arow.in_engine(rqrow):
                if first:
                    return arow
                else:
                    rows.append(arow)

        if rows:
            return rows

        # dig deeper?
        parent = self.meta.over()
        if parent:
            return parent.getrows(rowid, rqrow, colid, first)
        else:
            raise SysexLookupError(
                'row', self.meta.name,
                'no values found',
                (rowid, rqrow, colid))


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

    def aswiki(self):
        ''' render a table as a mediawiki table
        '''
        width = len(self.meta.cols) + 1
        over = self.meta.over() if self.meta.over else 'None'

        result = '{| class=wikitable width=90%\n'
        result += '|-\n'
        result += '! colspan=%s style="text-align:left"' % width
        result += '| %s\n' % self.meta.name
        result += "* Class: ''%s''\n" % self.__class__.__name__
        result += "* Overlays: ''%s''\n" % over
        result += "* keyid: %s\n" % self.keyid
        result += "* ident: %s\n" % self.ident
        result += '|- \n'
        result += '! |\n'
        for colid in self.meta.cols:
            if colid == '_PAD':
                continue
            result += '! style="text-align:left"| %s\n' % colid
        for arow in self._rows:
            result += arow.aswiki()
        result += '|}\n\n'
        return result

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, item, val):
        setattr(self, item, val)
        return val

    def __str__(self):
        result = '  Table Name: %s\n' % self.meta.name
        result += '    Colids: %s\n' % self.meta.cols
        result += '    KeyId: (*)%s\n' % self.keyid
        result += '    Ident: (@)%s\n' % self.ident
        result += '    Rows:\n'
        for arow in self._rows:
            result += '      %s\n' % arow

        return result


# pylint: disable=too-few-public-methods

## Table Subclasses, alphabetically
##

CLASSES = {}

def registered(cls):
    ''' decorator, registers classes in CLASSES
    '''
    CLASSES[cls.__name__] = cls
    return cls


@registered
class CTRLTable(Table):
    ''' Table
    '''
    pass

@registered
class DeviceTable(Table):
    ''' Table of Devices
    '''
    def __init__(self, mod, meta):
        super().__init__(mod, meta)

    def sniff(self, data, vendor):
        ''' ask the vendor sniff if it knows what this is
            - data: MIDI byte buffer
            - vendor: vendor ID detected by Vendor.mma_lookup()
            - return: specific device table row detected or None
        '''
        return algo.sniff(vendor, self, data)


@registered
class DrumTable(Table):
    ''' Table of Drum Properties
    '''
    def __init__(self, mod, meta):
        super().__init__(mod, meta)


@registered
class ChoiceTable(Table):
    ''' Table providing a way to select from groups of paramters
    '''
    def __init__(self, mod, meta):
        super().__init__(mod, meta)


@registered
class FMTable(Table):
    ''' Provide a description of operator routing for FM algorithms
    '''
    def __init__(self, mod, meta):
        super().__init__(mod, meta)



@registered
class FXTable(Table):
    ''' Table
    '''
    def __init__(self, mod, meta):
        super().__init__(mod, meta)


@registered
class HeaderTable(Table):
    ''' Header inside each device module
          will normally only be one line
    '''
    def __init__(self, mod, meta):
        super().__init__(mod, meta)


@registered
class IOTable(Table):
    ''' represent MIDI computer IO and MIDI routing devices
    '''
    def __init__(self, mod, meta):
        super().__init__(mod, meta)


@registered
class KBTable(Table):
    ''' Describe a keyboard device
    '''
    def __init__(self, mod, meta):
        super().__init__(mod, meta)


@registered
class KeyTable(Table):
    ''' keybed properties
    '''
    def __init__(self, mod, meta):
        super().__init__(mod, meta)


@registered
class ProtoTable(Table):
    ''' Device-specific Protocol
    '''
    def __init__(self, mod, meta):
        super().__init__(mod, meta)


@registered
class MemoryMap(Table):
    ''' table that maps a block of device addresses to properties
         each address can map to:
           a ParamTable row characterizing the value at that address
           a ChoiceTable providing a large (>5) number of value choices
           a MemoryMap with finer-grained mapping of part of the addr space
    '''
    def __init__(self, mod, meta):
        super().__init__(mod, meta)


@registered
class ParamTable(Table):
    ''' Table of Parameter Descriptions
    '''
    #! work out behringer and alesis bitfielding

    def __init__(self, mod, meta):
        super().__init__(mod, meta)

    def value(self, rowid, rqrow, midi):
        ''' convert a MIDI byte to a value
              the row provides semantics for interpreting the midi
              byte or bytes
        '''
        # get the row
        arow = self.get1row(rowid, rqrow)

        # if scale is (* val), scaling is done in MulCell
        # if scale is (]tab), scaling is done in ValueTable

        # remember: scale and shift are cells in the current row
        #  and that () gets the value of a cell
        #
        return arow.scale(
            arow.shift(
                algo.tovalue(arow.render(), midi)))

    def midi(self, rowid, rqrow, val):
        ''' convert value to a MIDI bytes
        '''
        arow = self.get1row(rowid, rqrow)

        # unscale
        scale = arow.scale()
        val = val / scale

        # unshift
        shift = arow.shift()
        val =- shift
        return algo.tomidi(arow.render(), val, arow.bytec())

    def vrange(self, rowid):
        ''' return the endpoints of the scaled range values
        '''
        pass


@registered
class SeqTable(Table):
    ''' Table
    '''
    def __init__(self, mod, meta):
        super().__init__(mod, meta)


@registered
class TGTable(Table):
    ''' Table
    '''
    def __init__(self, mod, meta):
        super().__init__(mod, meta)


@registered
class TOC(Table):
    ''' table of contents for a module
    '''
    def __init__(self, mod, meta):
        # force special name
        meta.name = 'TOC'
        super().__init__(mod, meta)


@registered
class ValueTable(Table):
    ''' table that maps MIDI byte values to float values
          used by many vendors in effects parameter translations
    '''
    def __init__(self, mod, meta):
        super().__init__(mod, meta)

    def value(self, data):
        ''' sparse lookup with interpolation
            - data: single MIDI data byte
        '''
        # pylint: disable=no-member
        #   pylint doesn't know cells

        # find the rows between which the midi byte falls
        ilast = flast = arow = 0
        for arow in self._rows:
            idata = arow.idata()
            if idata > data:
                break
            ilast = idata
            flast = arow.fdata()

        # interpolate
        return round(arow.scale() * (data - ilast) + flast, arow.prec())

    def midi(self, value):
        ''' sparse lookup with interpolation
            - value: floating value to be mapped to a MIDI byte
        '''
        # pylint: disable=no-member
        #   pylint doesn't know cells

        # find the rows between which the provided value falls
        dlast = flast = arow = 0
        for arow in self._rows:
            fdata = arow.fdata()
            if fdata > value:
                break
            flast = fdata
            dlast = arow.idata()

        # interpolate
        return int(
            round(arow.scale() * (value - flast) + dlast, 0))


@registered
class VendorTable(Table):
    ''' Table
    '''
    def __init__(self, mod, meta):
        super().__init__(mod, meta)
        for arow in self._rows:
            if arow.mma_id[0] == 0x00:
                arow['_idlen'] = 1
            else:
                arow['_idlen'] = 3

    def mma_lookup(self, data):
        ''' return the row matching the first 1 or 3 bytes in
              the data stream
        '''
        idlen = 1 if data[0] == 0x00 else 3
        arow = self.get1row(data[0:idlen], rqrow=None, colid='mma_id')
        return arow
