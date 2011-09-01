import random

from google.appengine.ext import db
from google.appengine.api import users

from infbase import Vect, Tile

# Block size.
SIZE = 50
# Probabilities for map generator.
PROBABILITY_MAP = [[5, 50, 30, 10, 30, 80, 90],
                   [0, 0, 65, 75, 85, 95, 100],
                   [0, 20, 0, 0, 0, 0, 100]]


class BlockModel(db.Model):
    """A database model to hold a 50x50 block of tiles."""
    x = db.IntegerProperty(required=True)
    y = db.IntegerProperty(required=True)
    tiletype = db.ListProperty(int)
    roll = db.ListProperty(int)


class SurroundingBlocks:
    """Nearbly map tile blocks.
    
    Used when generating a map. Will not generate map blocks if they do not
    already exist.
    """
    north = None
    south = None
    west = None
    east = None

    def __init__(self, pos):
        self.north = MapBlock(Vect(pos.x, pos.y - 1), generate_nonexist=False)
        self.south = MapBlock(Vect(pos.x, pos.y + 1), generate_nonexist=False)
        self.west = MapBlock(Vect(pos.x - 1, pos.y), generate_nonexist=False)
        self.east = MapBlock(Vect(pos.x + 1, pos.y), generate_nonexist=False)


class MapBlock:
    """A block of map tiles."""
    _pos = Vect(0,0)
    _block = None

    def __init__(self, pos, load=True, generate_nonexist=True):
        self._pos = pos.copy() 
        if load:
            self.load(generate_nonexist)
            if not self._block and generate_nonexist:
                self.generate()
                # TODO(craig): Atomic check + set to avoid race conditions.
                self.save()

    def load(self, generate_nonexist):
        # TODO(craig): Check memcached before performing DB query.
        # Database query.
        gql = "SELECT * FROM BlockModel WHERE x =: x AND y =: y LIMIT 1"
        query = db.GqlQuery(gql, x=self._pos.x, y=self._pos.x)
        result = list(query.fetch())
        if len(result):
            self._block = result[0]

    def save(self):
        db.put(self._block)

    def get(self, coord):
        t = coord.x + SIZE * coord.y
        return Tile(self._block.tiletype[t], self._block.roll[t])

    def set(self, coord, tile):
        t = coord.x + SIZE * coord.y
        self._block.tiletype[t] = tile.tiletype
        self._block.roll[t] = tile.roll

    def generate(self):
        self._block

    def exists(self):
        return self._block is not None

    def _getNeighbor(self, coord, d):
        out = coord.copy()
        if d is 1:
            out.y -= 1
        elif d is 4:
            out.y += 1
        else:
            if d is 0 or d is 5:
                out.x += 1
            elif d is 2 or d is 3:
                out.x -= 1
        if (not coord.x % 2) and (d is 0 or d is 2):
            out.y -= 1
        elif coord.x % 2 and (d is 3 or d is 5):
            out.y += 1
        return out

    def _sumLand(self, coord, surrounding_blocks):
        sum = 0
        t = None
        for i in range(6):
            n = self._getneighbor(coord, i)
            if n.x < SIZE and n.x >= 0 and n.y < SIZE and n.y >= 0:
                t = self.get(n)
            elif n.x < 0 and n.y < SIZE and n.y >= 0:
                t = surrounding_blocks.west.get(Vect(n.x + SIZE, n.y))
            elif n.x >= SIZE and n.y < SIZE and n.y >= 0:
                t = surrounding_blocks.east.get(Vect(n.x - SIZE, n.y))
            elif n.y < 0 and n.x < SIZE and n.x >= 0:
                t = surrounding_blocks.north.get(Vect(n.x, n.y + SIZE))
            elif n.y >= SIZE and n.x < SIZE and n.x >= 0:
                t = surrounding_blocks.south.get(Vect(n.x, n.y - SIZE))
            else:
                t = Tile()
            if t.isLand():
                sum += 1
        return sum

    def _generateTile(self, coord, surrounding_blocks, probabilities):
        sum = self._sumLand(coord, surrounding_blocks)
        t = Tile(0,0)
        # Land tile.
        if random.randint(1, 100) < PROBABILITY_MAP[sum]:
            t.randomize()
        self.set(coord, t)
