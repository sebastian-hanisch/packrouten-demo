"""Plattformfester Zufall: SplitMix64 nur mit Ganzzahlen (wörtlich wie in den Messreihen der Vormessung).

`uniform()` nimmt die oberen 53 Bit und multipliziert mit 2^-53 (exakt in Gleitkomma); es gibt keinen Aufruf von `math.log`, `math.cos` oder `hash()`.
Dieselbe Folge unter Windows und Linux (tests/test_rng.py)."""

_MASK = (1 << 64) - 1
_GAMMA = 0x9E3779B97F4A7C15
_M1 = 0xBF58476D1CE4E5B9
_M2 = 0x94D049BB133111EB


class SplitMix64:
    def __init__(self, seed):
        self.state = seed & _MASK

    def next(self):
        self.state = (self.state + _GAMMA) & _MASK
        z = self.state
        z = ((z ^ (z >> 30)) * _M1) & _MASK
        z = ((z ^ (z >> 27)) * _M2) & _MASK
        return z ^ (z >> 31)

    def uniform(self):
        return (self.next() >> 11) * (1.0 / (1 << 53))

    def below(self, k):
        return min(k - 1, int(self.uniform() * k))
