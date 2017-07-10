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


''' cell.py
      cell classes

    Cell: base class
        for scalars: int, float, string, True, False, None
      CListCell:
          compact representation for composite values - lists:
          a;b;..;z and members of subclasses.
          represented as [Cell(a), Cell(b), ..., Cell(z)]
        RangeCell:
            for things with discrete end points: a..b
            represented as [Cell(a), Cell(b)]
        SubstCell:
            for '(x a b ... z)' substitutions
            represented as [Cell(a), Cell(b), ..., Cell(z)]
            each operator 'x' is its own subclass
          ListCell:
              for composite values - lists: (a b ... z)
              provided as representation for rows with elipses
              any cell can also use this external representation
              it's a SubstCell because of '(...)' parse required
              represented as [Cell(a), Cell(b), ..., Cell(z)]
          OpCell:
              subclass for {+-&|~*%} substitutions
              inherits representation
            AndCell, AddCell, ,,,:
                one subclass for each of {<>+-&|~*%}
          HexCell:
              subclass for '#' substitutions
              inherits representation
          MatchCell:
              subclass for (= count dest [op] [match...]) substitutions
              inherits represenation
              required a bytearray and a dictionary,
                evaluates to a byte count
          ModCell:
              subclass for (! module) substitutions
              returns a reference to the named module
          TabCell:
              subclass for (] [mod] tab) substitutions
              returns a reference to the named table
          RowCell:
              subclass for (@ [[mod] tab] row) substitutions
              returns a reference to the named row
          ColCell:
              subclass for ($ [[[mod] tab] row] col) substitutions
              returns a reference to the named cell
          VarCell:
              subclass for (: name) substitutions
              evaluates to the value of 'name' from the current symbol table

    Parsing:
        conversion from external representation to internal representation
        is done by factories.
      Cell.factory():
          top-level parse for each cell
          detects CListCell (;) and RangeCell (..) syntax, dispatches
            constructor which will call Cell.factory() recursively
          detects top-level SubstCell and calls SubstCell.factory()
          any other value is a literal (int, str, None, True, False) and
            is returned via the Cell constructor
          always returns a Cell, a
      SubstCell.factory():
          determines substitution type by sniffing the character after '('
          gathers arguments from input buffer
          calls recursively to process any args that are substitutions
          returns the result of dispatching the required subclass constructor
'''

import re
import functools
from pysex import sysex

__all__ = ['Cell', 'ListCell']

# pylint: disable=too-few-public-methods
#   there is only one public interface to all of these:
#     __call__() computes and returns a value

def encast(val, number=False, base=10):
    ''' convert a string to an internal type
        - val: string to convert
        - return: val or val cast to float, int, False, True or None
    '''
    try:
        return int(val, base)
    except ValueError:
        pass

    try:
        return float(val)
    except ValueError:
        if number:
            raise ValueError(val)

    try:
        return {
            'yes':   True,
            'no':    False,
            'true':  True,
            'false': False,
            'none':  None
        }[val.lower()]
    except KeyError:
        pass

    return val


class Cell(object):
    ''' A Cell in our model
    '''
    @classmethod
    def factory(cls, loc, row, buf):
        ''' arrange to create an instance of Cell or subclass
            - loc: [f, r, c] location of this cell
            - buf: current cell or sub-cell contents
            - raise: ValueError on transitive '..'
            - return: an instance of a Cell subclass
        '''
        buf = buf.lstrip().rstrip()

        if buf.startswith('@'):
            # forced literal, save
            return Cell(loc, row, buf[1:])

        if buf.startswith('#'):
            # comment, no value
            return Cell(loc, row, None)

        parts = buf.split(';')
        if len(parts) > 1:
            # each part is its own cell
            return CListCell(loc, row, parts)

        parts = buf.split('..')
        if len(parts) == 2:
            # range expression
            return RangeCell(loc, row, parts)
        elif len(parts) > 2:
            raise ValueError(
                '%s: range cell syntax error: %s' % (
                    loc, buf))

        if buf.startswith('('):
            # cell is a substitution
            #  parse to internal represenation
            return SubstCell.factory(loc, row, buf[1:])

        # literal
        return Cell(loc, row, buf)

    def __init__(self, loc, row, val, **kwargs):
        ''' default ctor for all subclasses
            - loc: [f, r, c, [s]] location of this cell
            - row: reference to row holding this cell
            - val: value to store
        '''
        # pylint: disable=too-many-arguments
        self._loc = loc.copy()
        self._row = row
        if isinstance(val, str):
            self._value = encast(val, **kwargs)
        else:
            self._value = val

    def __str__(self):
        return '%s' % self._value

    def __call__(self, arg=None, syms=None):
        ''' default evaluator
            - arg=None: optional arg or context dictionary
            - return: current value of _value
        '''
        # Cell is stupid.  Just give them the value
        return self._value


class CListCell(Cell):
    ''' a cell which is a list of cells, used for RangeCells, ListCells
         and SubstCells
    '''
    def __init__(self, loc, row, parts, **kwargs):
        ''' create a cell containing subcomponents
              when called from Cell.factory(), parts will be strings
              when called from subclass (super().__init__(...),
                parts will be Cells
        '''
        # pylint: disable=too-many-arguments
        if parts and isinstance(parts[0], str):
            cells = []
            sloc = loc.copy()
            for nth, part in enumerate(parts):
                sloc['arg'] = nth
                cells.append(Cell.factory(sloc, row, part))
        else:
            cells = parts

        super().__init__(loc, row, cells, **kwargs)

    def __getitem__(self, item):
        return self._value[item]

    def __call__(self, arg=None, syms=None):
        ''' eval.  value is a list of the value of the sub-cells
            - arg=None: provided by caller
            - return: constituent list, all items evaluated
        '''
        return [val(arg, syms) for val in self[:]]

    def __str__(self):
        return ';'.join(['%s' % var for var in self[:]])


class RangeCell(CListCell):
    ''' class for v..v cells
    '''
    def __init__(self, loc, row, parts):
        ''' construct a RangeCell
              ListCell constructor handles the parsing of sub-components
        '''
        # pylint: disable=too-many-arguments
        super().__init__(loc, row, parts)

    def __call__(self, arg=None, syms=None):
        ''' evaluates to a range()
            - tab: subst context provider
            - arg: passthru to context
        '''
        vals = super().__call__(arg)

        if all([isinstance(val, int) for val in vals]):
            return range(vals[0], vals[1])

        raise ValueError(
            '%s: cannot make range from [%s, %s]' % (
                self._loc, vals[0], vals[1]))

    def __str__(self):
        return '..'.join(['%s' % val for val in self._value])


class CellIterator(object):
    ''' iterator class for parsing cell tokens
    '''
    def __init__(self, buf):
        ''' iterator ctor
            - buf: string to parse
        '''
        self._buf = buf

    def __iter__(self):
        return self

    def __next__(self):
        ''' yield next argument of a substitution
            - yield: next token if available
            - return: only when buf is exhausted
        '''
        self._buf = self._buf.lstrip()

        if not self._buf:
            raise StopIteration

        nextc = self.peek()

        if nextc in '(><#~&|-)!]@$:':
            self.advance(1)
            # substitution character
            return nextc

        if nextc == '%':
            # (% ...) subs use % args as ' ' and %% as '%'
            #   special handling required
            self.advance(1)
            if self.peek() == '%':
                self.advance(1)
                nextc += '%'
            return nextc

        mat = re.match(r"[^)\s]+", self._buf)
        if mat is None:
            raise StopIteration

        result = self._buf[mat.start():mat.end()]
        self.advance(mat.end())
        return result

    def peek(self):
        ''' return the next character without advancing
        '''
        return self._buf[0]

    def advance(self, count=1):
        ''' discard count characters
        '''
        self._buf = self._buf[count:]


class SubstCell(CListCell):
    ''' abstract base class of all substitutions
    '''
    @classmethod
    def factory(cls, loc, row, citer):
        ''' '(' was encountered on input
                next char determines specific subtype
            - loc: [f, r, c [,s]] of cell (for diagnostics)
            - row: row holding this cell
            - citer: CellIterator - token provider
        '''
        if isinstance(citer, str):
            citer = CellIterator(citer)

        # pylint: disable=too-many-arguments
        sigils = {
            # OpCells
            '+': AddCell,     # (+ v...):  additions
            '&': AndCell,     # (& v...):  bitwise AND
            '*': MulCell,     # (* v...):  multiplication
            '~': NotCell,     # (~ v...):  bitwise NOT
            '|': OrCell,      # (| v...):  bitwise OR
            '%': PasteCell,   # (% v...):  token pasting
            '<': ShiftLCell,  # (<< v...): bitwise shift left
            '>': ShiftRCell,  # (>> v...): bitwise shift right
            '-': SubCell,     # (- v...):  subtraction, unary negation
            # SubstCells
            '#': HexCell,     # (# v...):  hex values, hex strings
            '=': MatchCell,   # (= n t):   protocol matching
            '!': ModCell,     # (! module): lookup
            ']': TabCell,     # (] table):  lookup
            '@': RowCell,     # (@ row):    lookup
            '$': ColCell,     # ($ col):    lookup
            ':': VarCell      # (: var):    lookup
        }
        nextc = citer.peek()
        try:
            subclass = sigils[nextc]
            next(citer)
            if nextc in '<>':
                next(citer)
        except KeyError:
            # not listed, plain old ListCell
            subclass = ListCell

        numreq = nextc in '+&*~|<>-'
        radreq = 16 if nextc is '#' else 10

        args = []
        # parse substitution arguments
        sloc = loc.copy()
        for nth, token in enumerate(citer):
            sloc['arg'] = nth
            if token == '(':
                # arg is itself a substitution
                args.append(
                    SubstCell.factory(sloc, row, citer))

            elif token == ')':
                # end of substitution text
                break

            else:
                # plain old cell
                args.append(
                    Cell(sloc, row, token, number=numreq, base=radreq))

        return subclass(loc, row, args)

    def __init__(self, loc, row, args, **kwargs):
        ''' ctor.  make a list of cells from citer
            - loc: [f, r, c [,s]] for diagnosics
            - row: row holding this cell
            - args: cell subcomponents
            - number=False: require numeric value
            - base=10: radix.  will be 16 for (#v...)
        '''
        # pylint: disable=too-many-arguments,unidiomatic-typecheck
        if type(self) is SubstCell:
            # should only be called by subclasses
            raise sysex.CellError(
                '%s: attempt to instantiate abstract SubstCell', loc)

        # substitutions are just lists with semantics applied
        #  by the derived class
        super().__init__(loc, row, args, **kwargs)


class ListCell(SubstCell):
    ''' ListCell with a (...) external representation
    '''
    def __init__(self, loc, row, args, **kwargs):
        super().__init__(loc, row, args, **kwargs)

    def __str__(self):
        ''' intercept for special list representation
        '''
        return '(' + ' '.join(['%s' % val for val in self[:]]) + ')'


##
## OpCells: implement unary and binary operators
##

def _null_job(left, right):
    ''' default job.  subclass must set something better
          raise is a statement, not an expression: can't lambda
    '''
    # pylint: disable=unused-argument
    raise NotImplementedError


class OpCell(SubstCell):
    ''' Operator cells that can take an argument
    '''
    def __init__(
            self, loc, row, args, **kwargs):
        ''' specialize by adding a seed and a job
        '''
        # pylint: disable=unidiomatic-typecheck,too-many-arguments
        if type(self) is OpCell:
            # should only be called by subclasses
            raise sysex.CellError(
                '%s: attempt to instantiate abstract OpCell', loc)

        super().__init__(loc, row, args, **kwargs)
        self._job = kwargs['job']
        self._sign = kwargs['sign']

    def __call__(self, arg=None, syms=None):
        if len(self._value) == 1:
            # allow (op n) to be applied to a supplied arg
            return self._job(self[0](arg, syms), arg)

        vals = super().__call__(arg, syms)
        # every subclass provides an operation-neutral starter value
        return functools.reduce(self._job, vals[1:], vals[0])

    def __str__(self):
        result = '(%s ' % self._sign
        result += ' '.join(['%s' % val for val in self._value])
        result += ')'
        return result


class AddCell(OpCell):
    ''' implement (+ v v ...) substitution
    '''
    def __init__(self, loc, row, args):
        super().__init__(
            loc, row, args,
            sign='+', job=lambda x, y: x + y)


class AndCell(OpCell):
    ''' implement (& v v ...)
    '''
    def __init__(self, loc, row, args):
        super().__init__(
            loc, row, args,
            sign='+', job=lambda x, y: x & y)


class MulCell(OpCell):
    ''' implement (* v v ...)
    '''
    def __init__(self, loc, row, args):
        super().__init__(
            loc, row, args,
            sign='*', job=lambda x, y: x * y)


class NotCell(OpCell):
    ''' implement (~ v)
    '''
    def __init__(self, loc, row, args):
        super().__init__(
            loc, row, args,
            sign='~', job=lambda x, y: ~y)

    def __call__(self, arg=None, syms=None):
        if self[:]:
            return ~self[0]()
        else:
            return ~arg

class OrCell(OpCell):
    ''' implement (| v v ...) substitution
    '''
    def __init__(self, loc, row, args):
        super().__init__(
            loc, row, args,
            sign='|', job=lambda x, y: x | y)


class PasteCell(OpCell):
    ''' class for (% s s ...) substitutions
    '''
    def __init__(self, loc, row, args):
        ''' ctor
        '''
        def paste(left, right):
            ''' do the string pasting, escaping %% and % specials
            '''
            pmap = {'%': ' ', '%%': '%'}
            right = '%s' % right
            right = pmap[right] if right.startswith('%') else right
            return '%s%s' % (left, right)

        super().__init__(
            loc, row, args, number=False,
            sign='%', job=paste)


class ShiftLCell(OpCell):
    ''' implement (<< ...)
    '''
    def __init__(self, loc, row, args):
        super().__init__(
            loc, row, args,
            sign='<<', job=lambda x, y: y << x)


class ShiftRCell(OpCell):
    ''' implement (>> ...)
    '''
    def __init__(self, loc, row, args):
        super().__init__(
            loc, row, args,
            sign='>>', job=lambda x, y: y >> x)


class SubCell(OpCell):
    ''' implement (- v v ...)
    '''
    def __init__(self, loc, row, args):
        super().__init__(
            loc, row, args,
            sign='-', job=lambda x, y: x - y)


##
## Other substitution types
##

class HexCell(SubstCell):
    ''' implement (# vv ...), hex values, lists of hex values
    '''
    def __init__(self, loc, row, args):
        super().__init__(loc, row, args, number=True, base=16)

    def __call__(self, arg=None, syms=None):
        if len(self._value) == 1:
            # if there is only one value, return an int
            return self[0](arg, syms)
        else:
            # nope, return list of eval'd sub-cells
            return super().__call__(arg, syms)

    def __str__(self):
        result = '(#'
        for val in super().__call__():
            result += ' %02X' % val
        return result + ')'


class MatchCell(SubstCell):
    ''' implement (= n target)
    '''
    #
    def __init__(self, loc, row, args):
        super().__init__(loc, row, args)

    def __call__(self, data, syms):
        ''' evaluate a cell that picks values out of data
            - data: bytearray to be parsed
            - syms: symbol table for evaluating sub-cells
            - return: number of bytes matched
        '''
        # pylint: disable=signature-differs

        # gotta process this:
        # (= 1
        #    (#10)
        #    (>> 4 (& (#F0))))
        #    (= 1
        #       chan
        #       (& ( #0F))))
        #
        # and this:
        # (= 3 addr)
        #
        # Syntax:
        #  Match-Expr := (= bytec dest)
        #                | (= bytec dest Op-Expr)
        #                | (= bytec dest Match-Expr ...)
        #  bytec      := Cell int -> int
        #                | SubstCell -> int
        #  dest       := Cell -> string
        #                | SubstCell -> string
        #  Op-Expr    := OpCell -> bytes
        def store(dest, val, syms):
            ''' put a value in the symbol table
            '''
            syms[dest] = val

        def check(dest, val, syms):
            ''' check a current value
            '''
            # pylint: disable=unused-argument
            val = val.split()
            if len(val) == 1:
                val = val[0]
            if val != dest:
                raise ValueError(
                    '%s: byte stream mismatch: %s != %s' % (
                        self._loc, val, dest))

        val = self._value       # need control over eval of sub components

        bytec, dest, rest = val[0], val[1], val[2:]
        bytec = bytec(data, syms)
        bytec = bytec if bytec else len(data)

        # eval dest
        destfunc = store
        if isinstance(dest, HexCell):
            # dest is NULL, asserts a value
            destfunc = check

        dest = dest(data, syms)

        if len(rest):
            # rest is ([OpCell] [MatchCell...])
            if isinstance(rest[0], OpCell):
                # apply operation to bytec bytes before storing/testing
                opcell = rest[0]
                if bytec > 1:
                    raise ValueError(
                        '%s: cannot apply op %s to multibyte values' % (
                            self._loc, opcell))
                destfunc(dest, opcell(int(data[0]), syms))
                del rest[0]

            # remaining cells are MatchCells, iterate through them
            for cell in rest:
                if not isinstance(cell, MatchCell):
                    raise ValueError(
                        '%s: unexpected %s in MatchCell: %s' % (
                            self._loc, cell.__class__.name, cell))

                # apply recursively
                #  data will be a copy, updates to syms will bubble up
                cell(data[0:bytec], syms)

        else:
            destfunc(dest, data[0:bytec], syms)

        return bytec

    def __str__(self):
        return '(= ' + ' '.join(['%s' % var for var in self[:]]) + ')'


class RefCell(SubstCell):
    ''' base class of all ref cells
    '''
    def __init__(self, loc, row, args, **kwargs):
        super().__init__(loc, row, args, **kwargs)
        self._mark = '?'

    def __str__(self):
        result = '(%s ' % self._mark
        result += ' '.join(['%s' % val for val in self[:]])
        result += ')'
        return result


class ModCell(RefCell):
    ''' (! module)
    '''
    def __init__(self, loc, row, args):
        super().__init__(loc, row, args)
        self._mark = '!'

    def __call__(self, arg=None, syms=None):
        ''' look up a module
        '''
        # pylint: disable=unused-argument
        return sysex.modref(self[0]())


class TabCell(RefCell):
    ''' (] [mod] table)
    '''
    @classmethod
    def tab(cls, row, names):
        ''' look up a table by name, resolving module if needed
        '''
        if len(names) > 1:
            mod = sysex.modref(names[0]())
        else:
            mod = row.tab.mod

        return mod.tabs[names[-1]()]

    def __init__(self, loc, row, args, **kwargs):
        super().__init__(loc, row, args, **kwargs)
        self._mark = ']'

    def __call__(self, arg=None, syms=None):
        ''' look up a table
        '''
        return TabCell.tab(self._row, self[:])


class RowCell(RefCell):
    ''' (@ [[mod] tab] row)
    '''
    @classmethod
    def row(cls, row, names):
        ''' look up a row by name, resolving table if needed
        '''
        if len(names) > 1:
            tab = TabCell.tab(row, names[:-1])
        else:
            tab = row.tab

        rowid = names[-1]()

        # process shorthand references to cells in current row
        if rowid == '@':
            if row.tab.ident:
                rowid = row.tab.ident
            else:
                rowid = 'ident'
        elif rowid == '*':
            rowid = row.tab.keyid

        return tab.getrow(rowid, row)

    def __init__(self, loc, row, args):
        super().__init__(loc, row, args)
        self._mark = '@'

    def __call__(self, arg=None, syms=None):
        ''' look up a row
        '''
        return RowCell.row(self._row, self[:])


class ColCell(RefCell):
    ''' ($ [[[mod] tab] row] col])
    '''
    def __init__(self, loc, row, args):
        super().__init__(loc, row, args)
        self._mark = '$'

    def __call__(self, arg=None, syms=None):
        ''' look up a cell
        '''
        if len(self[:]) > 1:
            row = RowCell.row(self._row, self[:-1])
        else:
            row = self._row

        return row.get(self[-1]())


class VarCell(RefCell):
    ''' (:...)
    '''
    def __init__(self, loc, row, args):
        super().__init__(loc, row, args)
        self._mark = ':'

    def __call__(self, arg=None, syms=None):
        return syms[self[0]()]



##
## Unit Test
##

def run_test(tnum, value, arg=None, syms=None):
    ''' call the cell factory and print the results
    '''
    loc = {
        'mod': 'units',
        'tab': 'atab',
        'row': 1,
        'col': tnum
    }
    class TMod(object):
        def __init__(self, name):
            self.name = name
            self.tabs = {}
            sysex.modreg(name, self)

        def put(self, tab, name):
            self.tabs[name] = tab
            
    class TTab(object):
        def __init__(self, name, mod):
            self.name = name
            self.mod = TMod(mod)
            self.rows = {}
            self.mod.put(self, name)
            
        def put(self, row, name):
            self.rows[name] = row

        def getrow(self, name, rowid):
            return self.rows[name]
            
    class TRow(object):
        def __init__(self, name):
            self._cells = {}
            self.ident = None
            self.tab = TTab('street', 'town')
            self.tab.put(self, name)
            
        def stuff(self, cells, names):
            for nth, name in enumerate(names):
                if not self.ident:
                    self.ident = name
                self._cells[name] = cells[nth]
            self.tab.put(self, self.ident)
            return self

        def get(self, name):
            return self._cells[name]

    row = TRow('house')
    row.stuff(
        [ Cell.factory(loc, row, '1'),
          Cell.factory(loc, row, '2'),
          Cell.factory(loc, row, '3'),
          Cell.factory(loc, row, '99') ],
        [ 'a', 'b', 'c', 'mouse' ])

    cell = Cell.factory(loc, row, value)
    cval = cell(arg, syms)
    if isinstance(cval, int):
        print('%s: %s\n: %s (#%02X)\n' % (value, cell, cval, 0xFF&cval))
    else:
        print('%s: %s\n: %s\n' % (value, cell, cval))


def units():
    ''' run unit tests
    '''

    def test(start):
        ''' generate test numbers
        '''
        val = start
        while True:
            yield val
            val += 1

    tnum = test(0)
    arg = 5
    syms = { 'foo': 'Hi Mom!' }

    cases = [
        "hello",
        "42",
        "3.14",
        "hello;goodbye",
        "1..4",
        "(#40)..(#60)",
        "1.3..foo",
        "(#80)",
        "(#8)",
        "(#80 7E)",
        "(+ 10 (#80))",
        "(& (#C5) (#FF)",
        "(~ (#80))",
        "(| (#80) (#0C))",
        "(% foo %% (+ 3 5))",
        "(% foo % (+ 3 5))",
        "(% foo  (+ 3 5))",
        "(<< 4 1)",
        "(>> 5 (#80))",
        "(- 5 (#A))",
        "(foo)",
        "(foo bar)",
        "(:foo)",
        "($ mouse)",
        "(@ house)",
        "($ house mouse)",
        "(] street)",
        "(@ street house)",
        "($ street house mouse)",
        "(! town)",
        "(] town street)",
        "(@ town street house)",
        "($ town street house mouse)"
    ]

    for case in cases:
        try:
            run_test(next(tnum), case, arg, syms)
        except ValueError as exc:
            print(exc)
            pass


if __name__ == '__main__':
    units()
