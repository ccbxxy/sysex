#!/usr/bin/python
"""
    sysex.py - parser for sysex.csv
"""

import sys

class Record(object):
    def __init__(self, table, fields):
        self.table = table
        for num, name in enumerate(table.fields):
            setattr(self, name, fields[num])

    def as_wiki(self, fp):
        fp.write('|-\n||\n')
        for field in self.table.fields:
            fp.write('|| %s\n' % getattr(self, field))

class Table(object):
    def __init__(self, line, fp):
        line = line.rstrip()
        fields = line.split(',')
        self.name = fields[0][1:]
        self.fields = []
        while fields[-1] == '':
            fields.pop()
        
        for field in fields:
            if field.startswith(':'):
                field = field[1:]
                self.key = field
            self.fields.append(field)
            
        self.records = {}
        
        while True:
            line = fp.readline()
            if line == '':
                return

            if line.startswith('#'):
                continue

            line = line.rstrip()
            if len(line) == 0:
                continue
            
            fields = line.split(',')
            if fields[1] == '':
                return
            
            record = Record(self, fields)
            self.records[getattr(record, self.key)] = record

    def as_wiki(self, fp):
        fp.write('{| class="wikitable"\n')
        nfields = len(self.fields)
        fp.write('|-\n! colspan="%s" ! %s\n' % (nfields, self.name))
        for record in self.records:
            self.records[record].as_wiki(fp)
                
class SysEx(object):
    def __init__(self, fname):
        self.tables = {}
        with open(fname, "r") as fp:
            while True:
                line = fp.readline()
                if line == '':
                    return
            
                if line.startswith('#'):
                    continue
                if line.startswith(':'):
                    table = Table(line, fp)
                    self.tables[table.name] =  table
                else:
                    continue

    def as_wiki(self, fp):
        for table in self.tables:
            self.tables[table].as_wiki(fp)

if __name__ == '__main__':
    sysex = SysEx('sysex.csv')
    sysex.as_wiki(sys.stdout)
    
