#!/usr/bin/python
"""
    sysex.py - parser for sysex.csv
"""

class Record(object):
    def __init__(self, names, fields):
        for num, name in names.enumerate():
            setattr(self, name, fields[num])


class Table(object):
    def __init__(self, line, fp):
        line = line.rstrip()
        fields = line.split(',')
        self.name = fields[0][1:]
        self.fields = []
        for field in fields:
            if field.startswith(':'):
                field = field[1:]
                self.key = field
            self.fields.append(field)
            
        self.key = [f for f in self.fields if f.startswith(':')]
        self.key = self.key[0][1:]
        self.records = {}
        
        while True:
            line = fp.readline()
            if line == None:
                return

            if line.startswith('#'):
                continue

            line = line.rstrip()
            fields = line.split(',')
            if fields[1] == '':
                return
            
            record = Record(self.fields, fields)
            self.records[getattr(record, key)] = record
            
class SysEx(object):
    def __init__(self, fname):
        self.tables = []
        with open(fname, "r") as fp:
            while True:
                line = fp.readline()
                if line == None:
                    return
            
                if line.startswith('#'):
                    continue
                if line.startswith(':'):
                    table = Table(line, fp)
                    self.tables[table.name] =  table
                else:
                    continue


if __name__ == '__main__':
    sysex = Sysex('sysex.csv')
    print sysex.__dict__
    
