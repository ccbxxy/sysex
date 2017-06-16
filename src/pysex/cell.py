#!/usr/bin/python3

''' cell.py
      cell classes

    Cell: base class
        for scalars: int, float, string, True, False, None
      RangeCell:
          for integer ranges, evaluates to range() iterator
      ListCell:
          for value enumerations, evaluates to a list
      SubstCell:
          for '(...)' substitutions

'''

import re

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
            'True': True,
            'true': True,
            'False': False,
            'false': False,
            'None': None,
            'none': None
        }[val]
    except KeyError:
        return val


class CellIterator(object):
    ''' iterator class for parsing cell tokens
    '''
    # pylint: disable=too-few-public-methods

    def __init__(self, loc, buf):
        self._loc = loc
        self._buf = buf

    def __iter__(self):
        return self

    def __next__(self):
        ''' yield next argument of a substitution
            - loc: [f, r, c] of cell
            - buf: cell text
            - yield: next token if available
            - return: only when buf is exhausted
        '''
        self._buf = self._buf.lstrip()

        if len(self._buf) == 0:
            raise StopIteration

        nextc = self.peek()

        if nextc in '(><#~&|-)':
            self._buf = self._buf[1:]
            return nextc

        if nextc == '%':
            self._buf = self._buf[1:]
            if self.peek() == '%':
                self._buf = self._buf[1:]
                return '%%'
            else:
                return '%'

        mat = re.match(r"[^)\s]+", self._buf)
        if mat is None:
            raise StopIteration

        result = self._buf[mat.start():mat.end()]
        self._buf = self._buf[mat.end():]
        return result

    def peek(self):
        ''' return the next character without advancing
        '''
        return self._buf[0]


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
            # literal cell
            return Cell(loc, buf[1:])

        if buf.startswith('#'):
            return Cell(loc, '')

        parts = buf.split(';')
        if len(parts) > 1:
            cells = []
            for i, part in enumerate(parts):
                cells.append(Cell.factory(loc + [i], part))
            return ListCell(loc, cells)

        parts = buf.split('..')
        if len(parts) > 2:
            raise ValueError('cell %s: range value: "%s" syntax error' % (
                loc, buf))

        if len(parts) == 2:
            return RangeCell(
                loc, [Cell.factory(loc, part) for part in parts])

        if buf.startswith('('):
            return SubstCell.factory(loc, CellIterator(loc, buf[1:]))

        return Cell(loc, buf)

    def __init__(self, loc, buf):
        ''' default ctor for all subclasses
            - loc: [f, r, c] location of this cell
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

    # pylint: disable=unused-argument
    def value(self, context, arg=None):
        ''' default evaluator, only suitable for literal cells
            - context: object that can process symbolic lookups
            - return: current value of _value
        '''
        return self._value
    # pylint: enable=unused-argument


class ListCell(Cell):
    ''' class for x;y... cells
    '''
    def __init__(self, loc, value):
        super(ListCell, self).__init__(loc, value)

    def value(self, context, arg=None):
        ''' evaluate.
              self._value is a list of scalars and cells
        '''
        result = []
        for val in self._value:
            if isinstance(val, Cell):
                result.append(val.value(context, arg))
            else:
                result.append(val)

        return result


class RangeCell(Cell):
    ''' class for v..v cells
    '''
    def __init__(self, loc, buf):
        super(RangeCell, self).__init__(loc, buf)

    def value(self, context, arg=None):
        lef, rig = self._value
        if isinstance(lef, Cell):
            lef = lef.value(context, arg)
        if isinstance(rig, Cell):
            rig = rig.value(context, arg)

        if isinstance(lef, int) and isinstance(rig, int):
            return range(lef, rig)

        raise ValueError('%s: cannot make range from [%s, %s]' % (
            self._loc, lef, rig))


class SubstCell(Cell):
    ''' base class of all substitutions
    '''
    @classmethod
    def factory(cls, loc, citer):

        lookup = {
            '+':  AddCell,
            '&':  AndCell,
            '#':  HexCell,
            '~':  NotCell,
            '|':  OrCell,
            '%':  PasteCell,
            '<':  ShiftCell,
            '>':  ShiftCell,
            '-':  SubCell,
        }
        nextc = citer.peek()
        try:
            subclass = lookup[nextc]
            next(citer)
        except KeyError:
            subclass = VarCell

        return subclass(loc, citer)

    def __init__(self, loc, citer, number=False, base=10):
        # pylint: disable=no-member,unused-argument
        super(SubstCell, self).__init__(loc, [])

        def _fail(xxx, yyy):
            raise ValueError('bad SubstCell._op override')

        args = []
        for token in citer:
            if token == '(':
                args.append(SubstCell.factory(loc, citer))
                continue

            if token == ')':
                break

            if isinstance(token, str):
                try:
                    args.append(encast(token, number, base))
                except ValueError:
                    raise ValueError(
                        '%s: unexpected non-numeric arg: %s' % (
                            loc, token))
            else:
                args.append(token)

        self._op = _fail
        self._value = args

    def value(self, context, arg=None):
        ''' evaluate. self._value is always an array of at least 2 items
              pass values pairwise to self._op and accumulate results
        '''
        # pylint: disable=no-member
        result = self._value.pop(0)
        if isinstance(result, Cell):
            result = result.value(context, arg)

        for val in self._value:
            if isinstance(val, Cell):
                val = val.value(context, arg)

            # pylint: disable=assignment-from-no-return
            result = self._op(result, val)

        return result


class AddCell(SubstCell):
    ''' implement (+ v v ...) substitution
    '''
    def __init__(self, loc, citer):
        # pylint: disable=no-member
        #  thinks ._value is int/float
        super(AddCell, self).__init__(loc, citer, number=True)
        self._value.insert(0, 0)
        self._op = lambda x, y: x + y

class AndCell(SubstCell):
    ''' implement (& v v ...)
    '''
    def __init__(self, loc, citer):
        # pylint: disable=no-member
        #  thinks ._value is int/float

        super(AndCell, self).__init__(loc, citer, number=True)
        self._value.insert(0, 0xFFFFFFFF)
        self._op = lambda x, y: x & y


class HexCell(SubstCell):
    ''' implement (# vv ...)
    '''
    def __init__(self, loc, citer):
        # pylint: disable=no-member
        #  thinks ._value is int/float
        super(HexCell, self).__init__(loc, citer, number=True, base=16)
        self._value.insert(0, [])
        self._op = lambda x, y: x + [y]

    def value(self, context, arg=None):
        # pylint: disable=no-member
        #  thinks ._value is int/float
        val = super(HexCell, self).value(context, arg)
        if len(val) == 1:
            return val.pop()
        return val


class NotCell(SubstCell):
    ''' implement (~ v)
    '''
    def __init__(self, loc, citer):
        # pylint: disable=no-member
        #  thinks ._value is int/float
        super(NotCell, self).__init__(loc, citer, number=True)
        self._value.insert(0, 0)
        self._op = lambda x, y: ~y


class OrCell(SubstCell):
    ''' implement (| v v ...) substitution
    '''
    def __init__(self, loc, citer):
        # pylint: disable=no-member
        #  thinks ._value is int/float
        super(OrCell, self).__init__(loc, citer, number=True)
        self._value.insert(0, 0x00000000)
        self._op = lambda x, y: x | y


class PasteCell(SubstCell):
    ''' class for (% s s ...) substitutions
    '''
    def __init__(self, loc, citer):
        ''' ctor
        '''
        # pylint: disable=no-member
        def paste(s, t):
            ''' contatenate tokens, processing % and %% metachars
                - s: left side
                - t: right side
            '''
            # pylint: disable=invalid-name
            if t == '%':
                t = ' '
            elif t == '%%':
                t = '%'

            return '%s%s' % (s, t)

        super(PasteCell, self).__init__(loc, citer)
        self._value.insert(0, '')
        self._op = paste


class ShiftCell(SubstCell):
    ''' implement (<< ...), (>> ...)
    '''
    def __init__(self, loc, citer):
        token = next(citer)
        if token not in '<>':
            raise ValueError( '%s: unknown substitution: >%s' % (
                loc, token))

        super(ShiftCell, self).__init__(loc, citer, number=True)
        if token == '<':
            self._op = lambda lef, rig: lef << rig
        else:
            self._op = lambda lef, rig: lef >> rig


    def value(self, context, arg=None):
        def to_value(v, context, arg):
            ''' polymorphic value extraction
            '''
            # pylint: disable=invalid-name
            if isinstance(v, Cell):
                return v.value(context, arg)
            else:
                return v

        if len(self._value) == 2:
            arg, rig = [to_value(v, context, arg) for v in self._value]
        else:
            if arg is None:
                return 0
            rig = arg, self._value[0].value(context, arg)

        return self._op(arg, rig)


class SubCell(SubstCell):
    ''' implement (- v v ...)
    '''
    def __init__(self, loc, citer):
        # pylint: disable=no-member
        #   thinks self._value is int/float
        super(SubCell, self).__init__(loc, citer, number=True)
        if len(self._value) == 1:
            self._value.insert(0, 0)
        self._op = lambda x, y: x - y


class VarCell(SubstCell):
    ''' class for (]TableName)
    '''
    def __init__(self, loc, citer):
        # pylint: disable=no-member
        #  it thinks self._value is int or float
        nextc = citer.peek()
        if nextc == ']':
            scope = 't'
            next(citer)
        elif nextc == '*':
            scope = 'r'
            next(citer)
        else:
            scope = 'c'

        print( '! NEXTC, SCOPE: %s, %s' % (nextc, scope) )
        super(VarCell, self).__init__(loc, citer)
        self._value.insert(0, scope)

    def value(self, context, arg=None):
        return context.lookup(self._value, arg)


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
