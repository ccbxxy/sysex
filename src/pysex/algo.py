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


''' algo: data manipulation agorithms
'''


# pylint: disable=bad-whitespace

__all__ = ['tovalue', 'tomidi', 'sniffers', 'sniff']

_RCLASSES = {}

def _renderer(cls):
    ''' cheap registration decorator
    '''
    _RCLASSES[cls.__name__] = cls
    return cls

class Render(object):
    ''' data bytes to MIDI bytes conversions
    '''
    def __init__(self, width):
        self._width = width
        # 2^n - 1: 2^7 - 1 -> 0x7F
        self._bits = (1 << width) - 1

    def tomidi(self, val, bytec):
        ''' convert val to stream of MIDI bytes using specified _width
        '''
        result, temp = (val, [])
        while temp:
            result.insert(0, temp & self._bits)
            temp >>= self._width

        cbyte = len(result)
        if cbyte > bytec:
            raise ValueError(
                'value %d too big for %d bytes' % (val, bytec))

        while range(cbyte, bytec):
            result.insert(0, 0)

        return result

    def tovalue(self, midi):
        ''' convert from MIDI based of number of important bits
        '''
        result = 0
        for abyte in midi:
            result <<= self._width
            result += abyte

        return result


@_renderer
class AKAISCIIRender(Render):
    ''' AKAI Chars <-> 7-bit ASCII
    '''
    # pylint: disable=too-few-public-methods
    def __init__(self):
        super().__init__(1)

    charmap = {
        10: 0x20,          # Ascii Space
        37: 0x23,          # Ascii #
        38: 0x2B,          # Ascii +
        39: 0x2D,          # Ascii -
        40: 0x2E           # Ascii .
    }
    def tomidi(self, val, bytec):
        ''' to ascii
        '''
        if val in range(0,10):
            return val + 0x30   # Ascii 0-9
        if val in range(11,37):
            return val + 0x30   # Ascii A-Z

        try:
            return AKAISCIIRender.charmap[val]
        except KeyError:
            raise ValueError('unrecognized Akai char value: %d' % val)

    def tovalue(self, midi):
        if midi in range(0x30, 0x3A):
            return midi - 0x30
        if midi in range(0x3A, 0x5B):
            return midi - 0x30

        for _akai, _ascii in AKAISCIIRender.charmap.items():
            if midi == _akai:
                return _ascii

        raise ValueError('character not in Akai charset: %s' % chr(midi))


def hbbxl_midi(block):
    ''' convert up to seven bytes of 8 bit data
          to up to 8 bytes of 7 bit data
        - data:  array of bytes
        - bytec: number of data bytes to process
        - raise: IndexError if count out of range
        - return: new array of bytes
        '''
    bytec = len(block)
    if 1 > len(block) > 7:
        raise IndexError('block len %d: out of range' % bytec)

    msb = 0
    ret = []

    # start from the end so that the high bit of
    #  data[0] is the rightmost bit
    while bytec > 0:
        bytec -= 1
        bit = (block[bytec] & 0x80) >> 7
        msb <<= 1
        msb |= bit
        ret.insert(0, block[bytec] & 0x7F)

    return msb, ret

def hbbxl_value(hibits, midi):
    ''' convert up to seven bytes of 7 bit data to 8 bit
          data using bits from msb
        - hibits: ms bits of data, x6543210 order
        - midi:  array of bytes
    '''
    ret = []
    count = len(midi)
    for i in range(0,count):
        bit = (hibits & 0x01) << 7
        ret.append(midi[i] | bit)
        hibits >>= 1

    return ret

@_renderer
class HBB1HRender(Render):
    ''' convert midi stream <-> packed stream
          7 packed become 7 MIDI with 1 ms byte
          (1) ms byte sent first
          (H) msb for byte 0 is bit 0 of ms byte
    '''
    # pylint: disable=too-few-public-methods
    def __init__(self):
        super().__init__(0)

    def tomidi(self, data, bytec):
        ''' see class header
        '''
        pass

    def tovalue(self, midi):
        ''' midi will be a block of bytes
        '''
        pass


@_renderer
class HBB8LRender(Render):
    ''' convert midi stream <-> packed stream
          7 packed become 7 MIDI with 1 ms byte
          (8) ms byte sent last
          (L) msb for byte 0 is bit 7 of ms byte
    '''
    # pylint: disable=too-few-public-methods
    def __init__(self):
        super().__init__(0)

    def tomidi(self, val, bytec):
        hibits, mbytes = hbbxl_midi(val)
        mbytes.append(hibits)
        return mbytes

    def tovalue(self, midi):
        ''' convert up to seven bytes of 7 bit data to 8 bit
              data using bits from msb
              - midi:  array of bytes
        '''
        if 2 > len(midi) > 8:
            raise IndexError(
                'midi packet len %d: must be 2 < len < 8' % len(midi))

        return hbbxl_value(midi[0], midi[1:])


@_renderer
class NybbleRender(Render):
    ''' convert int <-> string of 0000bbbb bytes
    '''
    # pylint: disable=too-few-public-methods
    def __init__(self):
        super().__init__(4)



@_renderer
class MIDI7Render(Render):
    ''' convert int <-> bytes with 0 msb
    '''
    # pylint: disable=too-few-public-methods
    def __init__(self):
        super().__init__(7)


@_renderer
class UINT8Render(Render):
    ''' convert int <-> 8-bit bytes
    '''
    # pylint: disable=too-few-public-methods
    def __init__(self):
        super(UINT8Render, self).__init__(8)


_RINSTANCES = {}

def _xform(fun, name, *args):
    ''' dispatch a method call named fun once class instance name
          has been located
    '''
    try:
        return getattr(_RINSTANCES[name], fun)(args)
    except KeyError:
        pass

    try:
        _RINSTANCES[name] = _RCLASSES[name]()
        return _xform(fun, name, args)

    except KeyError:
        raise ValueError(
            'unknown renderer class: %s' % name)

def tomidi(name, val, bytec):
    ''' dispatch a value to MIDI transform
        - name: name of class to use
        - val: value to convert
    '''
    return _xform('tomidi', name, val, bytec)

def tovalue(name, midi):
    ''' dispatch a MIDI to value transform
        - name: name of instance to use
        - midi: array of MIDI bytes to convert
    '''
    return _xform('tovalue', name, midi)


# here come the sniffers, one per vendor
_SNIFFERS = {}

def _sniffer(fun):
    ''' decorator function to register a sniffer
    '''
    _SNIFFERS[fun.__name__] = fun
    return fun

# TEMPORARY
# pylint: disable=unused-argument

def _byte2sniffer(dev, data):
    return dev.getrows(
        data[1], rqrow=None, colid='proto_id', first=True)

@_sniffer
def akai(dev, data):
    ''' true if data stream looks like Akai data
    '''
    # model ID in byte 2
    return _byte2sniffer(dev, data)

@_sniffer
def alesis(dev, data):
    ''' true if data stream looks like Akai data
    '''
    pass

@_sniffer
def behr(dev, data):
    ''' true if data stream looks like Akai data
    '''
    pass

@_sniffer
def boss(dev, data):
    ''' true if data stream looks like Akai data
    '''
    pass

@_sniffer
def digi(dev, data):
    ''' true if data stream looks like Akai data
    '''
    pass

@_sniffer
def djtt(dev, data):
    ''' true if data stream looks like Akai data
    '''
    pass

@_sniffer
def dsi(dev, data):
    ''' true if data stream looks like Akai data
    '''
    pass

@_sniffer
def emu(dev, data):
    ''' true if data stream looks like Akai data
    '''
    pass

@_sniffer
def fishm(dev, data):
    ''' true if data stream looks like Akai data
    '''
    pass

@_sniffer
def kurz(dev, data):
    ''' true if data stream looks like Akai data
    '''
    pass

@_sniffer
def livid(dev, data):
    ''' true if data stream looks like Akai data
    '''
    pass

@_sniffer
def maudio(dev, data):
    ''' true if data stream looks like Akai data
    '''
    pass

@_sniffer
def megalite(dev, data):
    ''' true if data stream looks like Akai data
    '''
    pass

@_sniffer
def mucom(dev, data):
    ''' true if data stream looks like Akai data
    '''
    pass

@_sniffer
def nova(dev, data):
    ''' true if data stream looks like Akai data
    '''
    pass

@_sniffer
def rol(dev, data):
    ''' true if data stream looks like Akai data
    '''
    pass

@_sniffer
def rld(dev, data):
    ''' true if data stream looks like Akai data
    '''
    pass

@_sniffer
def yamaha(dev, data):
    ''' true if data stream looks like Yamaha data
        - dev: master device table
        - data: MIDI message, vendor ID removed
        - return: one row from the Device table
    '''
    # Yamaha puts device code (model id) at second byte
    #  master protocol lines: XG, QS300, etc. should be placed
    #  highest up on the table.  ie. all of the XG synths will
    #  dump as 0x4C, so for reading purposes, the master XG
    #  map is all we need
    return _byte2sniffer(dev, data)


def sniff(vendor, dev, data):
    ''' public interface: true if vendor sniffer is true
    '''
    try:
        return _SNIFFERS[vendor](dev, data)
    except KeyError:
        raise ValueError(
            'no sniffer registered for vendor %s' % vendor)

def sniffers():
    ''' public interface: get a list of available sniffers
    '''
    return _SNIFFERS.keys()
