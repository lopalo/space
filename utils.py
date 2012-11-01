from time import time
from functools import wraps
from math import *


def frame_rate(func):
    info = dict()
    @wraps(func)
    def new_func(*args, **kwargs):
        if not info:
            info['counter'] = 0
            info['next_time'] = time() + 1
        info['counter'] += 1
        now = time()
        if now >= info['next_time']:
            print '{0} {1} fps'.format(func.__name__, info['counter'])
            info['counter'] = 0
            info['next_time'] = now + 1
        return func(*args, **kwargs)
    return new_func


class Vect(object):

    def __init__(self, x=0.0, y=0.0):
        self.x = x
        self.y = y

    @classmethod
    def create(cls, len=0.0, angle=0.0):
        """Angle in degrees"""
        inst = cls()
        inst.len, inst.angle = len, angle
        return inst

    @property
    def coord(self):
        return self.x, self.y

    def clone(self):
        return self.__class__(self.x, self.y)

    @property
    def len(self):
        return hypot(self.x, self.y)

    @len.setter
    def len(self, val):
        k = atan2(self.y, self.x)
        self.x = val * cos(k)
        self.y = val * sin(k)

    @property
    def angle(self):
        return degrees(atan2(self.y, self.x))

    @angle.setter
    def angle(self, val):
        """Value in degrees"""
        len = hypot(self.x, self.y)
        self.x = len * cos(radians(val))
        self.y = len * sin(radians(val))

    def rotate(self, val):
        """Value in degrees"""
        self.angle = self.angle + val

    def reverse(self):
        return self.__class__(-self.x, -self.y)

    def __add__(self, other):
        cls = self.__class__
        assert isinstance(self, cls)
        return cls(self.x + other.x, self.y + other.y)

    def __iadd__(self, other):
        cls = self.__class__
        assert isinstance(other, cls)
        self.x += other.x
        self.y += other.y
        return self

    def __sub__(self, other):
        cls = self.__class__
        assert isinstance(other, cls)
        return cls(self.x - other.x, self.y - other.y)

    def __mul__(self, val):
        assert isinstance(val, (int, float))
        cls = self.__class__
        return cls(self.x * val, self.y * val)

    def __div__(self, val):
        assert isinstance(val, (int, float))
        cls = self.__class__
        val = float(val)
        return cls(float(self.x) / val, float(self.y) / val)

    def __repr__(self):
        cls = self.__class__.__name__
        return '{cls}({c[0]}, {c[1]})'.format(cls=cls, c=self.coord)
