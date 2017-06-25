#!/usr/bin/python3

''' syxmod.py
       module (file) processor
'''

# pylint: disable=bad-whitespace

import csv
import os
import copy
import contextlib
from pysex import sysex
from pysex import table
from pysex.cell import Cell

__all__ = ['Mod', 'ModEndException']

SOX = 0xF0
EOX = 0xF7
ACT = 0xFE

class ModEndException(Exception):
    ''' gratuitous specialization
    '''
    pass

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

        # idlen = 3
        # if midi[0] == 0x00:
        #     idlen = 1


class Mod(object):
    ''' Internal respresentation of a sysex CSV module
    '''
    # pylint: disable=too-few-public-methods
    def __init__(self, name):
        ''' ctor
            - name: dotted path to module
        '''
        if name.endswith('.csv'):
            fpath = name
            name = name[0:-4]
            parts = name.split(os.sep)
            name = '.'.join(parts)
        else:
            parts = name.split('.')
            fpath = os.sep.join(parts) + '.csv'

        self._name = name
        self.loc = {
            'name': name,
            'row':  0,
            'cell': 0,
            'arg':  0
        }
        self.tabs = {}
        self._load(fpath)
        self.reader = None
        sysex.mods[name] = self

    def _load(self, fpath):
        with open(fpath, newline='') as csvfile:
            self.reader = csv.reader(
                csvfile, fieldnames='', delimiter=',', dialect='unix')
            for line in self.reader:
                self.loc['row'] += 1

                if line[0].startswith[']']:
                    name = line[0][1:]
                    _class = line[1]
                    if line[2]:
                        # table says it's an overlay for another.
                        #  capture contents as a Cell to allow
                        #  (]tab) and (!mod tab) expansions
                        cloc = copy.copy(self.loc)
                        cloc['cell'] = 2
                        over = Cell(cloc, None, line[2])
                    else:
                        over = None
                try:
                    tab = table.CLASSES[_class](self, name, over)
                except ModEndException:
                    return

            self.tabs[tab.name] = tab
            setattr(self, tab.name, tab)

    def marshall(self, device, fpath):
        ''' convert a dump into pile of tables
            - device: device table for parsing dump
            - fpath: path to dump file
        '''
        # TEMORARY
        # pylint: disable=no-self-use
        with packets(fpath) as dumpdata:
            for data in dumpdata:
                device.marshall(data)
