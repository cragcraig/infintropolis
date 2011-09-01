import copy


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
