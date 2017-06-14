#!/usr/bin/python3

''' cell.py
      cell classes
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
        return {'True': True, 'False': False, 'None': None}[val]
    except KeyError:
        pass

    return val


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
        buf = buf.lstrip.rstrip()

        if buf.startswith('@'):
            # literal cell
            return Cell(loc, buf[1:])

        if buf.startswith('#'):
            return Cell(loc, None)

        parts = buf.split(';')
        if len(parts) > 1:
            return ListCell(
                loc, [Cell.factory(loc, part) for part in parts])

        parts = buf.split('..')
        if len(parts) > 2:
            raise ValueError('cell %s: range value: "%s" syntax error' % (
                loc, buf))

        if len(parts) == 2:
            return RangeCell(
                loc, [Cell.factory(loc, part) for part in parts])

        if buf.startswith('('):
            return SubCell(loc, buf[1:])

        return Cell(loc, buf)

    def __init__(self, loc, values):
        ''' default ctor for all subclasses
            - loc: [f, r, c] location of this cell
            - values: list of components of the cell
        '''
        self._loc = loc
        if not isinstance(values, str):
            self._values = values
        else:
            self._values = encast( values.rstrip().lstrip() )

    # pylint: disable=unused-argument
    def values(self, context, arg=None):
        ''' default evaluator, only suitable for literal cells
            - context: object that can process symbolic lookups
            - return: current value of _values
        '''
        return self._values
    # pylint: enable=unused-argument


class ListCell(Cell):
    ''' class for x;y... cells
    '''
    def values(self, context, arg=None):
        return [item.values(context, arg) for item in self._values]


class RangeCell(Cell):
    ''' class for v..v cells
    '''
    def values(self, context, arg=None):
        return range( self._values[0].values(context, arg),
                      self._values[1].values(context, arg) )


class SubstCell(Cell):
    ''' base class of all substitutions
    '''
    @classmethod
    def factory(cls, loc, buf):

        lookup = {
            '+':  AddCell,
            '&':  AndCell,
            '#':  HexCell,
            '~':  NotCell,
            '|':  OrCell,
            '%':  PasteCell,
            '<':  ShiftCell,
            '>':  ShiftCell,
            '-':  SubCell
        }
        try:
            subclass = lookup[buf[0]]
            buf = buf[1:]
        except KeyError:
            subclass = VarCell

        return buf, subclass(loc, buf.lstrip())

    # pylint: disable=unused-argument,no-self-use
    def _fail(self, xxx, yyy):
        raise ValueError('bad SubstCell._op override')

    # pylint: enable=unused-argument,no-self-use

    def __init__(self, loc, buf, number=False, base=10):
        super(SubstCell, self).__init__(self, loc, buf)

        for buf, val in self.subcell(loc, buf):
            if isinstance(val, str):
                try:
                    self._values.append(encast(val, number, base))
                except ValueError:
                    raise ValueError('unexpected non-numeric arg: %s' % val)
            else:
                self._values.append(val)

        self._op = self._fail


    def subcell(self, loc, buf):
        buf = buf.lstrip()
        if len(buf) == 0:
            return

        if buf.startswith('('):
            yield SubstCell(loc, buf[1:])

        mat = re.match(r"[\S]+", buf)
        yield buf[mat.end():], buf[mat.start():mat.end()]

    def values(self, context, arg=None):
        if not isinstance(self._values, list):
            raise ValueError('self._values is not a list')

        result = self._values.pop().values(context, arg)
        for val in self._values:
            result = self._op(result, val.values(context, arg))


class AddCell(SubstCell):
    ''' implement (+ v v ...) substitution
    '''
    def __init__(self, loc, buf):
        super(AddCell, self).__init__(self, loc, buf, number=True)
        self._op = lambda x, y: x + y


class AndCell(SubstCell):
    ''' implement (& v v ...)
    '''
    def __init__(self, loc, buf):
        super(AndCell, self).__init__(self, loc, buf, number=True)
        self._op = lambda x, y: x & y


class HexCell(SubstCell):
    ''' implement (# vv ...)
    '''
    def __init__(self, loc, buf):
        super(HexCell, self).__init__(self, loc, buf, number=True, base=16)
        self._values.insert(0, [])
        self._op = lambda x, y: x.append(y)


class NotCell(SubstCell):
    ''' implement (~ v)
    '''
    def __init__(self, loc, buf):
        super(NotCell, self).__init__(self, loc, buf, number=True)
        self._values.insert(0, 0)
        self._op = lambda x, y: ~y


class OrCell(SubstCell):
    ''' implement (| v v ...) substitution
    '''
    def __init__(self, loc, buf):
        super(OrCell, self).__init__(self, loc, buf, number=True)
        self._op = lambda x, y: x | y


class PasteCell(SubstCell):
    ''' class for (% s s ...) substitutions
    '''
    def __init__(self, loc, buf):
        def paste(s, t):
            if t == '%':
                t = ' '
            elif t == '%%':
                t = '%'

            return '%s%s' % (s, t)
                
        super(PasteCell, self).__init__(self, loc, buf)
        self._op = paste


class ShiftCell(SubstCell):
    ''' implement (<< ...), (>> ...)
    '''
    def __init__(self, loc, buf):
        super(ShiftCell, self).__init__(self, loc, buf[1:], number=True)
        if buf.startswith('<'):
            self._op = lambda lef, rig: lef << rig
        else:
            self._op = lambda lef, rig: lef >> rig


    def values(self, context, arg=None):
        if len(self._values) == 2:
            arg, rig = [v.values(context, arg) for v in self._values]
        else:
            if arg is None:
                return 0
            rig = arg, self._values[0].values(context, arg)

        return self._op(arg, rig)


class SubCell(SubstCell):
    ''' implement (- v v ...)
    '''
    def __init__(self, loc, buf):
        super(SubCell, self).__init__(self, loc, buf, number=True)
        if len(self._values) == 1:
            self._values.insert(0, 0)
        self._op = lambda x, y: x - y


class VarCell(SubstCell):
    ''' class for (* * *)
    '''
    def __init__(self, loc, buf):
        if buf.startswith(']'):
            scope = 't'
            buf = buf[1:]
        elif buf.startswith('*'):
            scope = 'r'
            buf = buf[1:]
        else:
            scope = 'cl'
            
        super(VarCell, self).__init__(self, loc, buf)
        self._values.insert(0, scope)

    def values(self, context, arg=None):
        return context.lookup(self._values, arg)






