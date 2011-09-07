import random

from google.appengine.ext import db
from google.appengine.api import users

from infbase import Vect, Tile, TileType

# Block size.
SIZE = 50
# Probabilities for map generator.
PROBABILITY_MAP = [[5, 50, 30, 10, 30, 80, 90],
                   [0, 0, 65, 75, 85, 95, 100],
                   [0, 20, 0, 0, 0, 0, 100]]


class BlockModel(db.Model):
    """A database model representing a 50x50 block of tiles."""
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
        """Load BlockModel from cache/database.

        By default a BlockModel will be generated and stored to the database
        if one does not exist.
        """
        self._pos = pos.copy() 
        if load:
            self.load()
            if not self._block and generate_nonexist:
                self.generate(PROBABILITY_MAP)
                # TODO(craig): Atomic check + set to avoid race conditions.
                self.save()

    def load(self):
        """Load or reload Block from cache/database."""
        # TODO(craig): Check memcache before performing DB query.
        gql = "SELECT * FROM BlockModel WHERE x = :x AND y = :y LIMIT 1"
        query = db.GqlQuery(gql, x=self._pos.x, y=self._pos.x)
        result = list(query.fetch(limit=1))
        if len(result):
            self._block = result[0]

    def save(self):
        """Store changes back to cache and database."""
        # TODO(craig): Store changes in memcache.
        #db.put(self._block)

    def get(self, coord):
        """Get the tile at a specified coordinate."""
        if not self._block:
            return Tile()
        t = coord.x + SIZE * coord.y
        return Tile(self._block.tiletype[t], self._block.roll[t])

    def fastGetTileType(self, x, y):
        return self._block.tiletype[x + SIZE * y]

    def set(self, coord, tile):
        """Set the tile at a specified coordinate."""
        t = coord.x + SIZE * coord.y
        self._block.tiletype[t] = tile.tiletype
        self._block.roll[t] = tile.roll

    def generate(self, prob_map):
        """Randomly generate the MapBlock."""
        self._block = BlockModel(x=self._pos.x, y=self._pos.y)
        self._clear()
        surrounding = SurroundingBlocks(self._pos)
        for t in xrange(len(prob_map)):
            i = SIZE
            for j in xrange(SIZE):
                i -= 1
                for k in xrange(j, i):
                    self._generateTile(Vect(j, k), surrounding, prob_map[t])
                for k in xrange(j, i):
                    self._generateTile(Vect(k, i), surrounding, prob_map[t])
                for k in xrange(i, j, -1):
                    self._generateTile(Vect(i, k), surrounding, prob_map[t])
                for k in xrange(i, j, -1):
                    self._generateTile(Vect(k, j), surrounding, prob_map[t])

    def exists(self):
        """Check if this MapBlock has been sucessfully loaded/generated yet."""
        return self._block is not None

    def getString(self):
        return ''.join([repr(self._block.tiletype[i]) + ':' +
                        repr(self._block.roll[i]) + ','
                        for i in xrange(SIZE * SIZE)])

    def _clear(self):
        self._block.tiletype = (SIZE * SIZE) * [TileType.water]
        self._block.roll = (SIZE * SIZE) * [0]

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
        sum = 0
        t = TileType.water
        n = Vect(0, 0)
        for i in xrange(6):
            self._getNeighbor(coord, i, n)
            if n.x < SIZE and n.x >= 0 and n.y < SIZE and n.y >= 0:
                t = self.fastGetTileType(n.x, n.y)
            elif (n.x < 0 and n.y < SIZE and n.y >= 0 and
                  surrounding_blocks.west.exists()):
                t = surrounding_blocks.west.fastGetTileType(n.x + SIZE, n.y)
            elif (n.x >= SIZE and n.y < SIZE and n.y >= 0 and
                  surrounding_blocks.east.exists()):
                t = surrounding_blocks.east.fastGetTileType(n.x - SIZE, n.y)
            elif (n.y < 0 and n.x < SIZE and n.x >= 0 and
                  surrounding_blocks.north.exists()):
                t = surrounding_blocks.north.fastGetTileType(n.x, n.y + SIZE)
            elif (n.y >= SIZE and n.x < SIZE and n.x >= 0 and
                  surrounding_blocks.south.exists()):
                t = surrounding_blocks.south.fastGetTileType(n.x, n.y - SIZE)
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
