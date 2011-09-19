import random

from google.appengine.ext import db
from google.appengine.api import memcache

import inf
from inf import Vect, Tile, TileType

# Probabilities for map generator.
PROBABILITY_MAP = [[5, 50, 30, 10, 30, 80, 90],
                   [0, 0, 65, 75, 85, 95, 100],
                   [0, 20, 0, 0, 0, 0, 100]]


class BlockModel(db.Model):
    """A database model representing a 50x50 block of tiles."""
    x = db.IntegerProperty(required=True)
    y = db.IntegerProperty(required=True)
    tiletype = db.ListProperty(int, indexed=False)
    roll = db.ListProperty(int, indexed=False)


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


class MapBlock(inf.DatabaseObject):
    """A block of map tiles."""
    _pos = Vect(0,0)

    def __init__(self, pos, load=True, generate_nonexist=True):
        """Load BlockModel from cache/database.

        By default a BlockModel will be generated and stored to the database
        if one does not exist.
        """
        self._pos = pos.copy() 
        if load:
            self.load(use_cached=True)
            if not self._model and generate_nonexist:
                self.generate(PROBABILITY_MAP)
                # TODO(craig): Atomic check + set to avoid race conditions.
                self.save()

    def get(self, coord):
        """Get the tile at a specified coordinate."""
        if not self._model:
            return Tile()
        t = coord.x + inf.BLOCK_SIZE * coord.y
        return Tile(self._model.tiletype[t], self._model.roll[t])

    def fastGetTileType(self, x, y):
        """Get the tiletype of the tile at (x, y) without any checks."""
        return self._model.tiletype[x + inf.BLOCK_SIZE * y]

    def fastGetRoll(self, x, y):
        """Get the roll value of the tile at (x, y) without any checks."""
        return self._model.roll[x + inf.BLOCK_SIZE * y]

    def set(self, coord, tile):
        """Set the tile at a specified coordinate."""
        t = coord.x + inf.BLOCK_SIZE * coord.y
        self._model.tiletype[t] = tile.tiletype
        self._model.roll[t] = tile.roll

    def generate(self, prob_map):
        """Randomly generate the MapBlock."""
        self._model = BlockModel(x=self._pos.x, y=self._pos.y)
        self._clear()
        surrounding = SurroundingBlocks(self._pos)
        for t in xrange(len(prob_map)):
            i = inf.BLOCK_SIZE
            for j in xrange(inf.BLOCK_SIZE):
                i -= 1
                for k in xrange(j, i):
                    self._generateTile(Vect(j, k), surrounding, prob_map[t])
                for k in xrange(j, i):
                    self._generateTile(Vect(k, i), surrounding, prob_map[t])
                for k in xrange(i, j, -1):
                    self._generateTile(Vect(i, k), surrounding, prob_map[t])
                for k in xrange(i, j, -1):
                    self._generateTile(Vect(k, j), surrounding, prob_map[t])

    def getString(self):
        """Construct a comma deliminated string MapBlock representation."""
        return ''.join([repr(int(self._model.tiletype[i])) + ':' +
                        repr(int(self._model.roll[i])) + ','
                        for i in xrange(inf.BLOCK_SIZE * inf.BLOCK_SIZE)])

    def getId(self):
        """Construct a unique consistant identifier string for the MapBlock."""
        return 'map_' + repr(int(self._pos.x)) + ',' + repr(int(self._pos.y))

    def getGQL(self):
        return  "SELECT * FROM BlockModel WHERE x = " + repr(self._pos.x) +\
                " AND y = " + repr(self._pos.y)

    def _clear(self):
        """Clear the MapBlock to all water tiles."""
        self._model.tiletype = ((inf.BLOCK_SIZE * inf.BLOCK_SIZE) *
                                 [TileType.water])
        self._model.roll = (inf.BLOCK_SIZE * inf.BLOCK_SIZE) * [0]

    @staticmethod
    def _getNeighbor(coord, d, out):
        """Get the first tile in direction d from the given coord."""
        out.x = coord.x
        out.y = coord.y
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
        """Sum the number of land tiles around the given tile coord."""
        # TODO(craig): Use list comprehensions instead for a speedup.
        sum = 0
        t = TileType.water
        n = Vect(0, 0)
        for i in xrange(6):
            self._getNeighbor(coord, i, n)
            if (n.x < inf.BLOCK_SIZE and n.x >= 0 and n.y < inf.BLOCK_SIZE and
                n.y >= 0):
                t = self.fastGetTileType(n.x, n.y)
            elif (n.x < 0 and n.y < inf.BLOCK_SIZE and n.y >= 0 and
                  surrounding_blocks.west.exists()):
                t = surrounding_blocks.west.fastGetTileType(
                    n.x + inf.BLOCK_SIZE, n.y)
            elif (n.x >= inf.BLOCK_SIZE and n.y < inf.BLOCK_SIZE and
                  n.y >= 0 and surrounding_blocks.east.exists()):
                t = surrounding_blocks.east.fastGetTileType(
                    n.x - inf.BLOCK_SIZE, n.y)
            elif (n.y < 0 and n.x < inf.BLOCK_SIZE and n.x >= 0 and
                  surrounding_blocks.north.exists()):
                t = surrounding_blocks.north.fastGetTileType(
                    n.x, n.y + inf.BLOCK_SIZE)
            elif (n.y >= inf.BLOCK_SIZE and n.x < inf.BLOCK_SIZE and
                  n.x >= 0 and surrounding_blocks.south.exists()):
                t = surrounding_blocks.south.fastGetTileType(
                    n.x, n.y - inf.BLOCK_SIZE)
            else:
                t = TileType.water
            if t is not TileType.water:
                sum += 1
        return sum

    def _generateTile(self, coord, surrounding_blocks, probabilities):
        """Generate a random tile, taking surrounding tiles into account."""
        sum = self._sumLand(coord, surrounding_blocks)
        t = self.get(coord)
        # Land tile.
        if random.randint(1, 100) < probabilities[sum]:
            t.randomize()
        self.set(coord, t)
