#!/usr/bin/python
'''
    sysex.py - parser for sysex.csv
 
'''




def dispatch(conf, arg):
    return conf[0](conf[1:], arg)

def lookup(syms, tableref, ident, inst, val):
    refcomps = tableref.split('.')
    row = syms[tableref[0]](ident, inst, val)
    if len(refcomps) > 1:
        return getattr(row, refcomps[1])
    else:
        return row

def do_token(cell):

    ix = 0

    if cell.startswith('@'):
        # literal
        return None, cell[1:]
    
    # lists
    parts = cell.split(';')
    if len(parts) > 1:
        value = []
        for part in parts:
            value.append( do_token(part)[1] )
        return None, value

    cell = parts.pop()
    
    # ranges
    parts = cell.split('..')
    if len(parts) > 1:
        x, left = do_token(parts[0])
        x, right = do_token(parts[1])
        return None, range( left, right )
        
    # anything else
    value = []
    while cell:
        if cell.startswith('['):
            iy = cell(']')
            arg = cell[1:iy]
            parts = arg.split()
            for part in parts:
                ival = int(part, 16)
                value.append( lambda symtab: ival )
            iy += 1
            if iy >= len(cell):
                return None, value
            else:
                return cell[iy:], value

        elif cell.startswith(':'):
            pass 



class Cell(object):
    def __init__(self, cell):
        self.cell = _value(cell)

    def _value(self, cell):
        # tokens:
        #  token;token;...       list of values
        #  token..token          range of values
        #  [nn]                  hex value
        #  [nn nn ...]           hex string
        #  (tab row col)         specific cell
        #  (*   row col)         specific cell in current table
        #  (*   *   col)         specific cell in current row
        #  (. col)                 shorthand
        #                          will fall back to environment
        #  (tab row)             specific row
        #  (*   row)             specific row in current table
        #  (tab)                 table
        #
        #  (+ token token ...)   eval tokens, add
        #  (- token token)       eval tokens, subtract
        #  (| token token ...)   eval tokens, logical or
        #  (& token token ...)   eval tokens, logical and
        #  (! token)             eval token, logical not
        #  (<< token1 token2)    eval tokens, shift token2 left token1 bits
        #  (>> token1 token2)    eval tokens, shift token2 right token1 bits
        #  (% token token ...)   concatenate tokens
        #
        #  all 
        parse_map = [
            ['[',   self._hex_string],
            ['(%',  self._paste     ],
            ['(<<', self._lshift    ],
            ['(>>', self._rshift    ],
            ['(+',  self._add       ],
            ['(-',  self._sub       ],
            ['(|',  self._bit_or    ],
            ['(&',  self._bit_and   ],
            ['(!',  self._bit_not   ],
            ['(',   self._lookup    ]
        }
        cell = cell.lstrip()

        if cell.startswith('#'):
            # comment
            return None

        if cell.startswith('@'):
            # literal string
            return cell[1:]

        # do x;y;z lists
        parts = cell.split(';')
        if len(parts) > 1:
            result = []
            for part in parts:
                result.append(self._tvalue(self._tokenize(part)))
            return result

        # then do a..b ranges
        parts = cell.split('..')
        if len(parts) > 2:
            raise ValueError('cell %s: non-binary ".." op' % cell)

        if len(parts) == 2:
            left, right = parts
            return Range( self._tokenize(left),
                          self._tokenize(right) )

        tlist = self._tokenize(cell)
        while tlist:
            
            
        
    
        
class Row(object):
    def __init__(self, names, cells):
        for num, name in names.enumerate():
            setattr(self, name, Cell(cells[num]))


class Table(object):
    def __init__(self, line, fp):
        ''' parse lines from input to create a table
            - line: current input line
            - fp:   input stream
        '''
        self.key = None
        self.meta = None
        self.cells = []
        self.rows  = []

        line = line.rstrip()
        cells = line.split(',')
        self.name = cells[0][1:]
        self._class = cells[1]
        
        while True:
            line = fp.readline()
            if line == None:
                return

            if line.startswith('#'):
                continue

            line = line.rstrip()
            cells = line.split(',')
            if not cells[1]
                return

            zero = cells.pop(0)
            if zero.startswith(']]'):
                # cell descriptions
                self.meta = cells
                continue

            if zero.startswith('*'):
                # cell labels
                for i in range(len(cells)):
                    if cell[i].startswith('*'):
                        cell[i] = cell[i][1:]
                        self.key = cell[i]

                self.cells = cells
                continue
            
            self.rows.append(Row(self.cells, cells))

            
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
                if line.startswith(']'):
                    table = Table(line, fp)
                    self.tables[table.name] =  table
                else:
                    continue


if __name__ == '__main__':
    sysex = Sysex('sysex.csv')
    print sysex.__dict__
    
