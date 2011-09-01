import copy
import random


class Vect:
    x = None
    y = None

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def copy(self):
        return copy.copy(self)


class Tile:
    tiletype = None
    roll = None

    def __init__(self, tiletype=None, roll=None):
        self.tiletype = tiletype
        self.roll = roll

    def copy(self):
        return copy.copy(self)

    def isWater(self):
        return self.tiletype is not None and self.tiletype is 0

    def isLand(self):
        return self.tiletype is not None and self.tiletype is not 0

    def isDesert(self):
        return self.tiletype is 7

    def isRollable(self):
        return self.isLand() and not self.isDesert()

    def randomize(self):
        self._randResource()
        if self.isRollable():
            self._randRoll()
        else
            self.roll = 0

    def _randRoll(self):
        self.roll = random.choice([2, 3, 3, 4, 4, 5, 5, 6, 6,
                                   8, 8, 9, 9, 10, 10, 11, 11, 12])

    def _randResource(self):
        t = random.randint(2, 7)
        if t is 7:
            t = random.randint(1, 20)
            if t is 1:
                t = 8
            elif t <= 4:
                t = 9
            elif t <= 12:
                t = 7
            else:
                t = random.randint(2, 6)
        self.tiletype = t


