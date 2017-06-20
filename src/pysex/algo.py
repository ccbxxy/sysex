#!/usr/bin/python3

''' algo: data manipulation agorithms
'''

# pylint: disable=bad-whitespace

class Render(object):
    ''' data bytes to MIDI bytes conversions
    '''
    def __init__(self, width):
        self._width = width
        # 2^n - 1: 2^7 - 1 -> 0x7F
        self._bits = (1 << width) - 1

    def midi(self, val, bytec):
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

    def value(self, midi):
        ''' convert from MIDI based of number of important bits
        '''
        result = 0
        for abyte in midi:
            result <<= self._width
            result += abyte

        return result


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
    def midi(self, val, bytec):
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

    def value(self, midi):
        if midi in range(0x30, 0x3A):
            return midi - 0x30
        if midi in range(0x3A, 0x5B):
            return midi - 0x30

        for akai, _ascii in AKAISCIIRender.charmap.items():
            if midi == akai:
                return _ascii

        raise ValueError('character not in Akai charset: %s' % chr(midi))


class HBB1HRender(Render):
    ''' convert midi stream <-> packed stream
          7 packed become 7 MIDI with 1 ms byte
          (1) ms byte sent first
          (H) msb for byte 0 is bit 0 of ms byte
    '''
    # pylint: disable=too-few-public-methods
    def __init__(self):
        super().__init__(0)

    def midi(self, val, bytec):
        ''' val will be a block of bytes
        '''
        pass

    def value(self, midi):
        ''' midi will be a block of bytes
        '''
        pass

class HBB8LRender(Render):
    ''' convert midi stream <-> packed stream
          7 packed become 7 MIDI with 1 ms byte
          (8) ms byte sent last
          (L) msb for byte 0 is bit 7 of ms byte
    '''
    # pylint: disable=too-few-public-methods
    def __init__(self):
        super().__init__(0)

    def midi(self, val, bytec):
        ''' val will be a block of bytes
        '''
        pass

    def value(self, midi):
        ''' midi will be a block of bytes
        '''
        pass

class NybbleRender(Render):
    ''' convert int <-> string of 0000bbbb bytes
    '''
    # pylint: disable=too-few-public-methods
    def __init__(self):
        super(NybbleRender, self).__init__(4)


class MIDI7Render(Render):
    ''' convert int <-> bytes with 0 msb
    '''
    # pylint: disable=too-few-public-methods
    def __init__(self):
        super(MIDI7Render, self).__init__(7)


class UINT8Render(Render):
    ''' convert int <-> 8-bit bytes
    '''
    # pylint: disable=too-few-public-methods
    def __init__(self):
        super(UINT8Render, self).__init__(8)

_ALGORITHMS = {
    'AKAISCII': AKAISCIIRender,
    'HBB.1H':   HBB1HRender,
    'HBB.8L':   HBB8LRender,
    'MIDI7':    MIDI7Render,
    'NYBBLE':   NybbleRender,
    'UINT8':    UINT8Render
}



ALGOMAP = {}
for algo, _class in _ALGORITHMS.items():
    ALGOMAP[algo] = _class()
