#!/usr/bin/python

RENDER = {
    'MIDI7':  { 'shift': 7, 'mask':  0x7F },
    'NYBBLE': { 'shift': 4, 'mask':  0x0F }
}

class EffectType2Row(object):
    def __init__(self, row):
        self.msb = row['msb']
        self.lsb = row['lsb']
        self.name = row['name']
        self.params = row['params']

    def to_midi(self):
        return [self.msb, self.lsb]

    def from_midi(self, mbytes):
        return self


class EffectTypes2(object):
    ''' Table of Effects indexed by two bytes
    '''
    def __init__(self, rows):
        self.rows = []
        for row in rows:
            self.rows.append(EffectType2Row(row))

    def __call__(self, value):
        ''' value is an array: [msb lsb]
        '''
        for row in self.rows:
            if row.msb == value[0] and row.lsb == value[1]:
                return row

        return None

class ValueRow(object):
    def __init__(self, row):
        self.data = int(row['data'])
        self.value = float(row['value'])
        self.factor = float(row['factor'])

        
class ValueTable(object):
    def __init__(self, rows):
        _rows = []
        for row in _rows:
            _rows.append(ValueRow(row))

        self.rows = _rows.sort(cmp=lambda x, y: x.data - y.data)
            
    def to_midi(self, val):
        for i, row in enumerate(self.rows)
            if row.value < val:
                break

        if i == 0:
            return self.rows[0].data

        i -= 1
        offset = (val - self.rows[i].value)/row.factor
        return int(round(self.rows[i].data + offset))

    def from_midi(self, mbyte):
        for i, row in enumerate(self.rows):
            if row.data < mbyte:
                break

        if i == 0:
            return self.rows[0].value

        i -= 1
        factor = mbyte - self.rows[i].data
        return (factor * row.factor) + self.rows[i].value


class EffectsParam(object):
    def __init__(self, context, pdict):
        self.number = int(pdict['number'])
        self.bytec = int(pdict['bytec'])
        self.engine = pdict['engine']
        self.name = pdict['name']
        try:
            self.value = int(pdict['value'])
        except KeyError:
            self.value = 0

        lo, hi = pdict['range'].split('..')
        self.loval = int(lo)
        self.hival = int(hi)
        self.render = RENDER[pdict['render']]
        self.offset = int(pdict['offset'])
        try:
            self.scale = float(pdict['scale'])
        except ValueError:
            self.scale = context.instance(pdict['scale'])
            
        self.units = pdict['units']

    def __call__(self, num, engine):
        for row in self.rows:
            if row.num == num and engine in self.engine:
                return row

        return None
                
    def to_midi(self):
        if isinstance(self.scale, float):
            value = self.value / self.scale
        else:
            value = self.scale.to_midi(self.value)
            
        value += self.offset
        if value < self.loval or value > self.hival:
            raise ValueError('value %d (%Xh) out of range'
                             % (value, value))

        result = []
        for i in range(0,bytec):
            result.push(0, value & self.render['mask'])
            value >>= self.render['shift']

        return result

    def from_midi(self, mmsg):
        value = 0
        shift = 0
        for b in mmsg:
            value += b << shift
            shift += self.render['shift']

        value -= self.offset
        if isinstance(self.scale, float):
            self.value = value * self.scale
        else:
            self.value = self.scale.from_midi(value)
            
        return self

