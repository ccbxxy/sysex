#!/usr/bin/python3

''' cell.py
      cell classes

    Cell: base class
        for scalars: int, float, string, True, False, None
      RangeCell:
          for integer ranges, evaluates to range() iterator
      SubstCell:
          for '(...)' substitutions

'''

import re
from pysex import table

# pylint: disable=bad-whitespace

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
            raise ValueError()

    try:
        return {
            'true':  True,
            'false': False,
            'none':  None
        }[val.lower()]
    except KeyError:
        return val


class CellIterator(object):
    ''' iterator class for parsing cell tokens
    '''
    # pylint: disable=too-few-public-methods

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

        if nextc in '(><#~&|-)':
            self.advance(1)
            # substitution character
            return nextc

        if nextc == '%':
            # (% ...) subs use % args as ' ' and %% as '%'
            #   special handling required
            self.advance(1)
            if self.peek() == '%':
                self.advance(1)
                return '%%'
            else:
                return '%'

        if nextc = ':':
            # sugar for run-time bindings
            self.advance(1)
            return '_' + self.__next__()
        
        mat = re.match(r"[^:)\s]+", self._buf)
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


class Cell(object):
    ''' A Cell in our model
    '''
    @classmethod
    def factory(cls, loc, buf):
        ''' arrange to create an instance of the appropriate subclass
            - loc: [f, r, c] location of this cell
            - buf: current cell or sub-cell contents
            - raise: ValueError on transitive '..'
            - return: an instance of a Cell subclass
        '''
        buf = buf.lstrip().rstrip()

        if buf.startswith('@'):
            # forced literal, save
            return Cell(loc, buf[1:])

        if buf.startswith('#'):
            # comment, no value
            return Cell(loc, None)

        # cells may contain lists of 'sub-cells'
        parts = buf.split(';')
        if len(parts) > 1:
            return Cell(
                loc,
                [ Cell.factory(loc + [i], part)
                  for i, part in enumerate(parts) ])

        # cells may contain integer ranges
        parts = buf.split('..')
        if len(parts) > 2:
            raise ValueError('cell %s: range value: "%s" syntax error' % (
                loc, buf))

        if len(parts) == 2:
            return RangeCell(
                loc, [Cell.factory(loc, part) for part in parts])

        # do we have a substitution?
        if buf.startswith('('):
            return SubstCell.factory(loc, CellIterator(buf[1:]))

        return Cell(loc, buf)

    def __init__(self, loc, buf):
        ''' default ctor for all subclasses
            - loc: [f, r, c, [s]] location of this cell
            - values: list of components of the cell
        '''
        self._loc = loc
        if isinstance(buf, str):
            self._value = encast(buf)
        else:
            self._value = buf

    def __str__(self):
        result = '( loc: %s, value: ' % self._loc
        if isinstance(self._value, list):
            for val in self._value:
                result += '\n  %s' % val
        else:
            result += '%s' % self._value

        return result + ')'

    def value(self, rqrow, arg=None):
        ''' default evaluator
            - rqrow:  
            - return: current value of _value
        '''
        if isinstance(self._value, list):
            return [self.value(tab, arg) for val in self._value]
        else:
            return self._value


class RangeCell(Cell):
    ''' class for v..v cells
    '''
    def __init__(self, loc, buf):
        super(RangeCell, self).__init__(loc, buf)

    def value(self, tab, arg=None):
        ''' evaluates to a range()
            - tab: subst context provider
            - arg: passthru to context
        '''
        vals = super().value(tab, arg)

        if all([isinstance(val, int) for val in vals]):
            return range(vals[0], vals[1])

        raise ValueError('%s: cannot make range from [%s, %s]' % (
            self._loc, vals[0], vals[1]))


class SubstCell(Cell):
    ''' base class of all substitutions
    '''
    @classmethod
    def factory(cls, loc, citer):
        ''' '(' was encountered on input
                next char determines specific subtype
            - loc: [f, r, c [,s]] of cell (for diagnostics)
            - citer: CellIterator - token provider
        '''
        lookup = {
            '+':  AddCell,      # (+ v...):  additions
            '&':  AndCell,      # (& v...):  bitwise AND
            '#':  HexCell,      # (# v...):  hex values, hex strings
            '*':  MulCell,      # (* v...):  multiplication
            '~':  NotCell,      # (~ v...):  bitwise NOT
            '|':  OrCell,       # (| v...):  bitwise OR
            '%':  PasteCell,    # (% v...):  token pasting
            '<':  ShiftCell,    # (<< v...): bitwise shift left
            '>':  ShiftCell,    # (>> v...): bitwise shift right
            '-':  SubCell,      # (- v...):  subtraction, unary negation
        }
        nextc = citer.peek()
        try:
            subclass = lookup[nextc]
            next(citer)
        except KeyError:
            # ([[tab] row] cell) reference
            subclass = VarCell

        return subclass(loc, citer)

    def __init__(self, loc, citer, number=False, base=10):
        ''' ctor
            - loc: [f, r, c [,s]] for diagnosics
            - citer: CellIterator
            - number=False: require numeric value
            - base=10: radix.  will be 16 for (#v...)
        '''
        # pylint: disable=no-member,unused-argument

        # cell with empty list
        super(SubstCell, self).__init__(loc, [])
        self._seed = None

        args = []
        # parse substitution arguments
        for token in citer:
            if token == '(':
                # arg is itself a substitution
                args.append(SubstCell.factory(loc, citer))
                continue

            if token == ')':
                # end of substitution text
                break

            if isinstance(token, str):
                try:
                    args.append(encast(token, number, base))
                    # raises value error if number was required
                    #   note that substitutions were diverted earlier
                    #   and will not be evaluated until used

                except ValueError:
                    raise ValueError(
                        '%s: unexpected non-numeric arg: %s' % (
                            loc, token))
            else:
                args.append(token)

        self._value = args

    def method(self, left, right):
        ''' way to perform substitution operation on arguments
             makes this class virtual
        '''
        raise NotImplementedError

    def value(self, row, arg=None):
        ''' evaluate. self._value is always an array of at least 2 items
              pass values pairwise to self.method and accumulate results
            - tab: context provider
            - arg=None: is context dependent
        '''
        # pylint: disable=no-member

        # every subclass provides an operation-neutral starter value
        result = self._seed
        vals = super().value(row, arg)
        for val in vals:
            result = self.method(result, val)

        return result


class AddCell(SubstCell):
    ''' implement (+ v v ...) substitution
    '''
    def __init__(self, loc, citer):
        super(AddCell, self).__init__(loc, citer, number=True)
        self._seed = 0

    def method(self, left, right):
        # pylint: disable=no-self-use
        return left + right


class AndCell(SubstCell):
    ''' implement (& v v ...)
    '''
    def __init__(self, loc, citer):
        super(AndCell, self).__init__(loc, citer, number=True)
        self._seed = 0xFFFFFFFF

    def method(self, left, right):
        # pylint: disable=no-self-use
        return left & right


class HexCell(SubstCell):
    ''' implement (# vv ...)
    '''
    def __init__(self, loc, citer):
        super().__init__(loc, citer, number=True, base=16)

    def method(self, left, right):
        # never called
        pass

    def value(self, tab, arg=None):
        # expand all substitutions
        val = super().value(tab, arg)

        # return single hex values as scalars
        if len(val) == 1:
            # pylint: disable=no-member
            #  thinks ._value is int/float
            return val.pop()

        # ... but longer lists as lists
        return val


class MulCell(SubstCell):
    ''' implement (* v v ...)
    '''
    def __init__(self, loc, citer):
        super().__init__(loc, citer, number=True)
        self._seed = 1

    def method(self, left, right):
        # pylint: disable=no-self-use
        return left * right


class NotCell(SubstCell):
    ''' implement (~ v)
    '''
    def __init__(self, loc, citer):
        super().__init__(loc, citer, number=True)
        # pylint: disable=no-member
        #  thinks ._value is int/float
        self._seed = 0

    def method(self, left, right):
        # pylint: disable=unused-argument,no-self-use
        return ~right


class OrCell(SubstCell):
    ''' implement (| v v ...) substitution
    '''
    def __init__(self, loc, citer):
        super().__init__(loc, citer, number=True)
        self._seed = 0x00000000

    def method(self, left, right):
        # pylint: disable=no-self-use
        return left | right


class PasteCell(SubstCell):
    ''' class for (% s s ...) substitutions
    '''
    def __init__(self, loc, citer):
        ''' ctor
        '''
        super().__init__(loc, citer)
        self._seed = ''

    def method(self, left, right):
        # pylint: disable=no-self-use
        pmap = {'%': ' ', '%%': '%'}
        right = pmap[right] if right.startswith('%') else right
        return '%s%s' % (left, right)


class ShiftCell(SubstCell):
    ''' implement (<< ...), (>> ...)
    '''
    def __init__(self, loc, citer):
        token = next(citer)
        if token not in '<>':
            raise ValueError( '%s: unknown substitution: >%s' % (
                loc, token))

        super().__init__(loc, citer, number=True)
        if token == '<':
            self._shift = self._lshift
        else:
            self._shift = self._rshift

    def method(self, tab, arg=None):
        pass

    def _lshift(self, left, right):
        # pylint: disable=no-self-use
        return right << left

    def _rshift(self, left, right):
        # pylint: disable=no-self-use
        return right >> left

    def value(self, tab, right=None):
        if len(self._value) == 2:
            left, right = super().value(tab, right)
        else:
            if right is None:
                return 0
            left = self._value[0]

        return self._shift(left, right)


class SubCell(SubstCell):
    ''' implement (- v v ...)
    '''
    def __init__(self, loc, citer):
        super().__init__(loc, citer, number=True)
        self._seed = 0

    def method(self, left, right):
        return left - right


class VarCell(SubstCell):
    ''' class for (]TableName)
    '''
    def __init__(self, loc, citer):
        # pylint: disable=no-member
        #  it thinks self._value is int or float
        nextc = citer.peek()
        if next == '!':
            self._lookup = self._filex
            next(citer)
        elif nextc == ']':
            self._lookup = self._tabx
            next(citer)
        elif nextc == '@':
            self._lookup = self._rowx
            next(citer)
        else:
            self._lookup = self._colx

        super().__init__(loc, citer)

    def method(self, left, right):
        # pylint: disable=no-self-use,unused-argument
        pass

    def _colx(self, params):
        ''' get Cell reference
            - sargs: expanded substitution parameters
            - arg: pass-thru
        '''
        if len(params) > 1:
            row = self._rowx(params[:-1])

        return row.get(params[0])

    def _rowx(self, params):
        if len(params) > 1:
            tab = self._tabx(params[:1])

        return tab.row_select(params[0], row.keyval())

    def _tabx(self, args, tab, row):
        # pylint: disable=no-self-use,unused-argument
        return table.Table.get(args[0])

    def value(self, arg=None):
        return self._lookup(super().value(arg))


def run_test(context, test, value):
    ''' call the cell factory and print the results
    '''
    cell = Cell.factory([0, test, value], value)
    value = cell.value(context)
    if isinstance(value, int):
        print('%s\n: %s (#%X)\n' % (cell, value, 0xFF&value))
    else:
        print('%s\n: %s\n' % (cell, value))

def units():
    ''' run unit tests
    '''
    class Table(object):
        ''' provide a context for var substitutions
        '''
        # pylint: disable=too-few-public-methods
        def __init__(self):
            self._syms = {
                'foo': "banana"
            }

        def lookup(self, sym, arg):
            ''' dereference a symbol
            '''
            # pylint: disable=unused-argument
            print( '! SYM: %s' % sym )
            return self._syms[sym[1]]


    context = Table()

    def test(start):
        ''' generate test numbers
        '''
        val = start
        while True:
            yield val
            val += 1

    tnum = test(0)

    run_test(context, next(tnum), "hello")
    run_test(context, next(tnum), "42")
    run_test(context, next(tnum), "3.14")
    run_test(context, next(tnum), "hello;goodbye")
    run_test(context, next(tnum), "1..4")
    run_test(context, next(tnum), "(#40)..(#60)")

    try:
        run_test(context, next(tnum), "1.3..foo")
    except ValueError as err:
        print('! caught expected ValueError:\n!   %s\n' % err)

    run_test(context, next(tnum), "(#80)")
    run_test(context, next(tnum), "(#8)")
    run_test(context, next(tnum), "(#80 7E)")
    run_test(context, next(tnum), "(+ 10 (#80))")
    run_test(context, next(tnum), "(& (#C5) (#FF)")
    run_test(context, next(tnum), "(~ (#80))")
    run_test(context, next(tnum), "(| (#80) (#0C))")
    run_test(context, next(tnum), "(% foo %% (+ 3 5))")
    run_test(context, next(tnum), "(% foo % (+ 3 5))")
    run_test(context, next(tnum), "(% foo  (+ 3 5))")
    run_test(context, next(tnum), "(<< 4 1)")
    run_test(context, next(tnum), "(>> 5 (#80))")
    run_test(context, next(tnum), "(- 5 (#A))")
    run_test(context, next(tnum), "(foo)")



if __name__ == '__main__':
    units()
