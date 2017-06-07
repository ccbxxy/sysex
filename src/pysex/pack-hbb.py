#!/usr/bin/python


def hbb_8to7(count, data):
    """ convert up to seven bytes of 8 bit data
         to up to 8 bytes of 7 bit data
        - count: number of data bytes to process
        - data:  array of bytes
        - raise: IndexError if count out of range
        - return: msb_byte, new array of bytes
    """
    if 1 > count > 7:
        raise IndexError('count %d: out of range' % count)
    
    msb = 0
    ret = bytearray(count)

    # start from the end so that the high bit of
    #  data[0] is the rightmost bit
    while count > 0:
        count -= 1
        bit = (data[count] & 0x80) >> 7
        msb <<= 1
        msb |= bit
        ret[count] = data[count] & 0x7F

    return msb, ret

def hbb_7to8(count, data, msb):
    """ convert up to seven bytes of 7 bit data to 8 bit
         data using bits from msb
         - count: number of bytes in data
         - data:  array of bytes
         - msb:   byte containing MSB bits for elements of data
         - raise: Index error if count < 1 or > 7
         - return: array of count bytes
    """
    if 1 > count > 7:
        raise IndexError('count %d: out of range' % count)

    ret = bytearray(count)
    for i in range(0,count):
        bit = (msb & 0x01) << 7
        ret[i] = data[i] | bit
        msb >>= 1

    return ret

if __name__ == '__main__':
    eights = [0x80, 0x85, 0x70, 0x75, 0x95]

    print eights
    msb, bbs = hbb_8to7(len(eights), eights)
    print '0x%02X' % msb 
    for b in bbs: 
        print '0x%02X ' % b,

    print
    bbs = hbb_7to8(len(bbs), bbs, msb)
    for b in bbs:
        print '0x%02X ' % b,

