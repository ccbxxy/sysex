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

import copy

__all__ = ['Picto', 'PictoBox', 'PictoArrow', 'HEAD', 'BASE']

HEAD = 'AH'                        # arrow terminus
BASE = 'BA'                        # arrow terminus
NONE = 'NO'                        # arrow terminus

# pylint: disable=multiple-statements

# boxes
ULC = u'┌'; HOR = u'─'; URC = u'┐'
VER = u'│'; SPC = u' '
LLC = u'└';             LRC = u'┘'

# arrows
BDN = u'┬'                      # base down
ADN = u'▼'                      # arrow down
AUP = u'▲'                      # arrow up
BUP = u'┴'                      # base up
BRI = u'├'                      # base right
ARI = u'▶'                      # arrow right
ALE = u'◀'                      # arrow left
BLE = u'┤'                      # base left

# pylint: enable=multiple-statements

class Picto(object):
    ''' manage a canvas with a picture on it using ascii
          chars or UTF8 drawing characters
    '''
    def __init__(self, hlen, vlen, blob=None):
        ''' fourth quadrant coordinates
        '''
        if blob:
            canvas = []
            for row in blob:
                canvas.append(list(row))
            vlen = len(canvas)
            hlen = max([len(lin) for lin in canvas])
            if not all([hlen == len(lin) for lin in canvas]):
                raise ValueError(
                    'all lines must be the same length')
        else:
            canvas = [[' '] * hlen for lin in range(vlen)]

        self._can = canvas
        self.hlen = hlen
        self.vlen = vlen

    def __getitem__(self, index):
        return self._can[index]

    def __setitem__(self, index, val):
        self._can[index] = val

    def grow(self, rows=None, cols=None):
        ''' add (before, after), (before, after) cells to a canvas
        '''
        if rows:
            # add rows first
            head, tail = rows
            newrow = [' '] * self.hlen
            for row in range(head):
                self._can = [newrow] + self._can
            for row in range(tail):
                self._can += [newrow]
            self.vlen += head + tail

        if cols:
            head, tail = cols
            hcols = [' '] * head
            tcols = [' '] * tail
            for row in range(self.vlen):
                self[row] = hcols + self[row] + tcols
            self.hlen += head + tail

        return self

    def draw(self, hoff, voff, raster, trans=True):
        ''' place raster in self at [hoff,voff]
            - raster: image to add
            - hoff: horiz offset for upper left corner
            - voff: vert offset for upper left corner
            - trans: transparent: overwrite with only non-space chars
        '''
        # optimize?
        if not trans and hoff == 0 and raster.hlen == self.hlen:
            for off, row in enumerate(raster):
                self[off+voff] = copy.copy(row)
            return self

        for row in range(raster.vlen):
            if not trans:
                self[row][hoff:hoff+raster.hlen] = copy.copy(raster[row])
                continue
            for col in range(raster.hlen):
                if trans and raster[row][col] == ' ':
                    continue
                self[row+voff][col+hoff] = raster[row][col]

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
        ''' make a box
        '''
        lin = HOR * (hlen-2)
        spc = ' ' * (hlen-2)

        blob = [ULC + lin + URC]
        blob += (vlen-2) * [(VER + spc + VER)]
        blob += [LLC + lin + LRC]

        super().__init__(hlen, vlen, blob)

    def label(self, text):
        ''' insert text into box
        '''
        horc = int(self.hlen / 2)
        verc = int(self.vlen / 2)
        txtc = int(len(text)/2)
        hpos = horc - txtc
        return self.draw(verc, hpos, Picto(len(text), 1, [text]))


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
            chars = {
                'dn': { 'AH': ADN, 'BA': BUP, 'NO': SPC },
                'up': { 'AH': AUP, 'BA': BDN, 'NO': SPC },
            }
            return mid(hlen, chars[updn][lend], SPC, chars[updn][rend])

        def mid(hlen, lend, mid, rend):
            return lend + mid * (hlen-2) + rend

        def end(leri, xend):
            chars = {
                'ri': { 'AH': ARI, 'BA': BLE, 'NO': HOR },
                'le': { 'AH': ALE, 'BA': BRI, 'NO': HOR }
            }
            return chars[leri][xend]
            
        if vlen == 0:
            # direct arrow, orient and add ends
            blob = [mid(hlen, end('le', lend), HOR, end('ri', rend))]

        elif vlen < 0:
            blob  = [ mid(hlen, ULC, HOR, URC)]          # ┌──────┐
            blob += [ mid(hlen, VER, SPC, VER)           # │      │
                      for row in range(0, abs(vlen)-1) ] # │      │
            blob += [base(hlen, 'dn', lend, rend)]       # ▼      ┴


        else:
            blob  = [base(hlen, 'up', lend, rend)] # ┬      ▲
            blob += [ mid(hlen, VER, SPC, VER)     # │      │
                      for row in range(0, vlen-1)] # │      │
            blob += [ mid(hlen, LLC, HOR, LRC)]    # └──────┘
            
        super().__init__(hlen, vlen+1, blob)


class PictoVArrow(Picto):
    ''' vertical arrows
    '''
        
if __name__ == '__main__':
    # pylint: disable=invalid-name
    box = Picto(15, 5)
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

    box = Picto(40, 20)
    op1 = PictoBox(13, 5).label('Operator1')
    op2 = PictoBox(13, 5).label('Operator2')
    
    box.draw(5, 8, op1)
    box.draw(20, 8, op2)
    box.draw(13, 7,  PictoHArrow(10, -1, BASE, HEAD))
    box.draw(13, 12, PictoHArrow(10, 1, HEAD, BASE))
    print(box)
    
