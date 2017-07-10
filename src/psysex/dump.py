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


''' dump.py
      message IO
'''

# pylint: disable=bad-whitespace

import contextlib
from psysex import sysex

SOX = 0xF0
EOX = 0xF7
ACT = 0xFE

def consume_to(stream, thing):
    ''' skip bytes in stream until thing
    '''
    while True:
        mbyte = stream.read(1)
        if len(mbyte) == 0:
            return mbyte

        if mbyte == thing:
            return mbyte

@contextlib.contextmanager
def packets(fpath):
    ''' get next message from stream
        - return: array of midi data bytes absent F0, F7 framing
    '''
    with open(fpath, 'rb') as stream:
        while True:
            mbyte = consume_to(stream, SOX)
            if len(mbyte) == 0:
                return

            midi = []

            while True:
                mbyte = stream.read(1)
                if len(mbyte) == 0:
                    return

                if mbyte == ACT:
                    continue

                if mbyte == EOX:
                    yield midi
                    break

                midi.append(mbyte)



def load(fpath):
    ''' convert a dump into pile of tables
        - fpath: path to dump file
    '''
    # pylint: disable=unused-variable
    #! under construction
    master = sysex.modref(sysex.MASTER)
    with packets(fpath) as dumpdata:
        device = None
        for data in dumpdata:
            if not device:
                # assumes all sysex packets in the file are from
                #  the same device
                # device = Device.lookup(data)
                pass

            #device.load(data)
