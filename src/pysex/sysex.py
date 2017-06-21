#!/usr/bin/python
"""
    sysex.py - parser for sysex.csv
"""

import sys
from pysex import table

        
class SysEx(object):
    def __init__(self, fname):

        self._loadfile(fname)

    def _loadfile(self, fname):
        with open(fname, "r") as fp:
            while True:
                line = fp.readline()
                if line == '':
                    return
            
                if line.startswith('#'):
                    continue
                
                if line.startswith(']'):
                    table.Table.factory(fp, fname, line)
                else:
                    continue

    def _get_message(fp):
        message = {}

        while True:
            mbyte = fp.read(1)
        
    def marshall(self, fname):
        with open(fname, 'rb') as fp:
            msg = self._get_message(fp)
            self._store(msg)

        
    def as_wiki(self, fp):
        for tab in table.Table.tables():
            tab.as_wiki(fp)

