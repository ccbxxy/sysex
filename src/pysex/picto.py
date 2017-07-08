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

''' picto.py -
      "And now for something completely different..."
           https://www.youtube.com/watch?v=1f-kfRREA8M

      classes for doing text diagrams of modulation routing
'''

# pylint: disable=bad-whitespace

__all__ = ['Picto', 'PictoBox', 'PictoHArrow', 'HEAD', 'BASE', 'NONE']

HEAD = 'AH'                        # arrow terminus
BASE = 'BA'                        # arrow terminus
NONE = 'NO'                        # arrow terminus


class Picto(object):
    ''' manage a canvas with a picture on it using ascii
          chars or UTF8 drawing characters
    '''
    # pylint: disable=multiple-statements

    # box chars
    ULC = u'┌'; HOR = u'─'; URC = u'┐'
    VER = u'│'; SPC = u' '
    LLC = u'└';             LRC = u'┘'

    # arrow chars
    BDN = u'┬'                      # base down
    ADN = u'▼'                      # arrow down
    AUP = u'▲'                      # arrow up
    BUP = u'┴'                      # base up
    BRI = u'├'; ARI = u'▶'          # base, arrow right
    ALE = u'◀'; BLE = u'┤'          # arrow, base left
    # pylint: enable=multiple-statements

    @classmethod
    def blank(cls, hlen, vlen):
        ''' create a blank canvas
            - hlen: width
            - vlen: height
            - return: a new blank canvas
        '''
        return cls([[Picto.SPC] * hlen for lin in range(vlen)])

    def __init__(self, blob):
        ''' ctor: convert blob to self
            - blob: array of strings
        '''
        can = [list(row) for row in blob]
        self.vlen = len(blob)
        self.hlen = max([len(lin) for lin in blob])
        for row in range(len(blob)):
            short = self.hlen - len(can[row])
            if short:
                can[row] += [Picto.SPC] * short
        self._can = can

    def __getitem__(self, index):
        return self._can[index]

    def __setitem__(self, index, val):
        self._can[index] = val

    def grow(self, rows=None, cols=None):
        ''' add (before, after), (before, after) cells to a canvas
        '''
        # add full-width rows first
        if rows:
            head, tail = rows
            newrow = [[Picto.SPC] * self.hlen]
            # before
            for row in range(head):
                self._can = newrow + self._can
            # after
            for row in range(tail):
                self._can += newrow
            self.vlen += head + tail

        if cols:
            head, tail = cols
            hcols = [Picto.SPC] * head
            tcols = [Picto.SPC] * tail
            for row in range(self.vlen):
                self[row] = hcols + self[row] + tcols
            self.hlen += head + tail

        return self

    def draw(self, hoff, voff, pic, trans=True):
        ''' place pic in self at [hoff,voff]
            - pic:  Picto image to add
            - hoff: horiz offset for upper left corner
            - voff: vert offset for upper left corner
            - trans: transparent: overwrite with only non-space chars
        '''
        #! at some point, have Picto keep a table of drawn objects
        #!  and their locations.  Have __str__ do the compositing.
        #! this will allow 'erase' and 'move'

        # optimize?
        if not trans and hoff == 0 and pic.hlen == self.hlen:
            for off, row in enumerate(pic):
                self[off+voff] = row[:] # slice-copy
            return self

        for row in range(pic.vlen):
            if not trans:
                self[row][hoff:hoff+pic.hlen] = pic[row][:]
                continue
            for col in range(pic.hlen):
                if trans and pic[row][col] == Picto.SPC:
                    continue
                self[row+voff][col+hoff] = pic[row][col]

        return self

    def __str__(self):
        result = ''
        for lin in range(self.vlen):
            result += ''.join(self[lin]) + '\n'
        return result


class PictoBox(Picto):
    ''' a box class that can take a label
    '''
    def __init__(self, hlen, vlen):
        ''' make a hlen * vlen box
        '''
        lin = Picto.HOR * (hlen-2)
        spc = Picto.SPC * (hlen-2)

        blob = [Picto.ULC + lin + Picto.URC]
        blob += (vlen-2) * [(Picto.VER + spc + Picto.VER)]
        blob += [Picto.LLC + lin + Picto.LRC]

        super().__init__(blob)

    def label(self, text):
        ''' insert text into box
        '''
        horc = int(self.hlen / 2)
        verc = int(self.vlen / 2)
        txtc = int(len(text)/2)
        hpos = horc - txtc
        return self.draw(verc, hpos, Picto([text]))


class PictoHArrow(Picto):
    ''' horizontal arrows
    '''
    def __init__(self, hlen, vlen, lend=NONE, rend=HEAD):
        ''' ctor
            - hlen: how long
            - vlen: how tall, +: route under, -: route over
            - lend: left end in {HEAD, BASE or None}
            - lend: right end in {HEAD, BASE or None}
        '''
        def base(hlen, updn, lend, rend):
            ''' do arrows and bases
                - hlen: how wide
                - updn: orientation in {'up', 'dn'}
                - lend: left end in {HEAD, BASE, NONE}
                - rend: right end in in {HEAD, BASE, NONE}
                - return: assembled string
            '''
            chars = { 'dn': { 'AH': Picto.ADN,
                              'BA': Picto.BUP,
                              'NO': Picto.SPC },
                      'up': { 'AH': Picto.AUP,
                              'BA': Picto.BDN,
                              'NO': Picto.SPC } }
            return mid(hlen, chars[updn][lend], Picto.SPC, chars[updn][rend])

        def mid(hlen, lend, mid, rend):
            ''' do a middle row
                - hlen: how wide
                - lend: left end in {HEAD, BASE, NONE}
                - mid:  run char, presumably Picto.HOR or Picto.SPC
                - rend: right end in {HEAD, BASE, NONE}
                - return: assembled string
            '''
            return lend + mid * (hlen-2) + rend

        def end(leri, xend):
            ''' get end characters for flat arrows
                - leri: in {'le', 'ri'}
                - xend: end type in {HEAD, BASE, NONE}
            '''
            chars = { 'ri': { 'AH': Picto.ARI,
                              'BA': Picto.BLE,
                              'NO': Picto.HOR },
                      'le': { 'AH': Picto.ALE,
                              'BA': Picto.BRI,
                              'NO': Picto.HOR } }
            return chars[leri][xend]

        if vlen == 0:
            # direct arrow, orient and add ends
            blob = [mid(hlen, end('le', lend), Picto.HOR, end('ri', rend))]

        elif vlen < 0:
            # 1: ┌──────┐
            # 2: │      │
            # 3: ▼      ┴
            blob  = [ mid(hlen, Picto.ULC, Picto.HOR, Picto.URC)] # 1
            blob += [ mid(hlen, Picto.VER, Picto.SPC, Picto.VER)  # 2
                      for row in range(0, abs(vlen)-1) ]          # 2
            blob += [base(hlen, 'dn', lend, rend)]                # 3


        else:
            # 1: ┬      ▲
            # 2: │      │
            # 3: └──────┘
            blob  = [base(hlen, 'up', lend, rend)]                # 1
            blob += [ mid(hlen, Picto.VER, Picto.SPC, Picto.VER)  # 2
                      for row in range(0, vlen-1)]                # 2
            blob += [ mid(hlen, Picto.LLC, Picto.HOR, Picto.LRC)] # 3

        super().__init__(blob)


class PictoVArrow(Picto):
    ''' vertical arrows.  not needed yet
    '''

if __name__ == '__main__':
    # pylint: disable=invalid-name
    box = Picto.blank(15, 9)
    print(box)
    box = box.draw(2, 0, PictoBox(13, 5).label('Operator1'))
    print('Box:\n%s' % box)

    box.grow((1, 2), (3, 4))
    print('Labeled:\n%s' % box)

    print(PictoHArrow(8, 0, HEAD, HEAD))
    print(PictoHArrow(8, 0, HEAD, BASE))
    print(PictoHArrow(8, 0, BASE, HEAD))
    print(PictoHArrow(8, 0, HEAD, NONE))
    print(PictoHArrow(8, 0, NONE, HEAD))

    print(PictoHArrow(8, 3, HEAD, HEAD))
    print(PictoHArrow(8, 3, HEAD, BASE))
    print(PictoHArrow(8, 3, BASE, HEAD))
    print(PictoHArrow(8, 3, HEAD, NONE))
    print(PictoHArrow(8, 3, NONE, HEAD))

    print(PictoHArrow(8, -3, HEAD, HEAD))
    print(PictoHArrow(8, -3, HEAD, BASE))
    print(PictoHArrow(8, -3, BASE, HEAD))
    print(PictoHArrow(8, -3, HEAD, NONE))
    print(PictoHArrow(8, -3, NONE, HEAD))

    box = Picto.blank(40, 20)
    op1 = PictoBox(13, 5).label('Operator1')
    op2 = PictoBox(13, 5).label('Operator2')

    box.draw(5, 8, op1)
    box.draw(20, 8, op2)
    box.draw(13, 7,  PictoHArrow(10, -1, BASE, HEAD))
    box.draw(13, 12, PictoHArrow(10, 1, HEAD, BASE))
    print(box)

