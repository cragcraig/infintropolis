import copy
import random


class Vect:
    """Vector containing an (x,y) coordinate pair."""
    x = None
    y = None

    def __init__(self, x, y):
        self.x = int(x)
        self.y = int(y)

    def copy(self):
        return copy.copy(self)


class Tile:
    """An individual resource tile."""
    tiletype = None
    roll = None

    def __init__(self, tiletype=None, roll=None):
        self.tiletype = tiletype
        self.roll = roll

    def copy(self):
        return copy.copy(self)

    def isWater(self):
        return self.tiletype is not None and self.tiletype is TileType.water

    def isLand(self):
        return (self.tiletype is not None and
                self.tiletype is not TileType.water)

    def isDesert(self):
        return self.tiletype is TileType.desert

    def isRollable(self):
        return self.isLand() and not self.isDesert()

    def randomize(self):
        self._randResource()
        if self.isRollable():
            self._randRoll()
        else:
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


class TileType:
    none, water, field, pasture, forest, hills, mountain, desert, \
        goldmine, volcano, fish = range(11)
