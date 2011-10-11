import random

from google.appengine.ext import db
from google.appengine.api import memcache

import inf
from inf import Vect, Tile, TileType
from buildableblock import BuildableBlock
from buildable import BuildType

# Probabilities for map generator.
PROBABILITY_MAP = [[3, 30, 10, 10, 30, 80, 90],
                   [0, 0, 50, 75, 85, 95, 80],
                   [0, 20, 0, 0, 0, 0, 100]]
#PROBABILITY_MAP = [[5, 50, 30, 10, 30, 80, 90],
#                   [0, 0, 65, 75, 85, 95, 100],
#                   [0, 20, 0, 0, 0, 0, 100]]


class BlockModel(db.Model):
    """A database model representing a 50x50 block of tiles."""
    x = db.IntegerProperty(required=True, indexed=True)
    y = db.IntegerProperty(required=True, indexed=False)
    tiletype = db.ListProperty(int, indexed=False)
    roll = db.ListProperty(int, indexed=False)


class SurroundingMapBlocks:
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
    modelClass = BlockModel
    _pos = Vect(0,0)
    _buildableBlock = None

    def __init__(self, pos, load=True, generate_nonexist=True, buildable_block=None):
        """Load BlockModel from cache/database.

        By default a BlockModel will be generated and stored to the database
        if one does not exist.
        """
        self._pos = pos.copy()
        self._buildableBlock = buildable_block
        if load:
            self.load()
            if not self._model and generate_nonexist:
                self.generate(PROBABILITY_MAP)
                self.loadOrCreate(x=self._pos.x, y=self._pos.y,
                                  tiletype=self._model.tiletype,
                                  roll=self._model.roll)

    def getPos(self):
        return self._pos

    def get(self, coord):
        """Get the tile at a specified coordinate."""
        if not self._model:
            return Tile()
        t = coord.x + inf.BLOCK_SIZE * coord.y
        return Tile(self._model.tiletype[t], self._model.roll[t])

    def fastGetTileType(self, x, y):
        """Get the tiletype of the tile at (x, y) without any checks."""
        return self._model.tiletype[x + inf.BLOCK_SIZE * y]

    def getTileType(self, pos):
        """Get the tiletype of the tile at pos(x, y) without any checks."""
        return self._model.tiletype[pos.x + inf.BLOCK_SIZE * pos.y]

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
        surrounding = SurroundingMapBlocks(self._pos)
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
        return ''.join([str(int(self._model.tiletype[i])) + ':' +
                        str(int(self._model.roll[i])) + ','
                        for i in xrange(inf.BLOCK_SIZE * inf.BLOCK_SIZE)])

    def getKeyName(self):
        return 'mapblock:' + str(self._pos.x) + ',' + str(self._pos.y)

    def getBuildableBlock(self):
        if not self._buildableBlock:
            self._buildableBlock = BuildableBlock(self._pos)
        return self._buildableBlock

    def findOpenSpace(self):
        """Find an open space for a new capitol, if possible.
        
        Returns either False or a tuple (Vect(block), Vect(pos)).
        """
        bb = self.getBuildableBlock()
        blist = None
        if bb:
            blist = bb.getBuildablesList()
        bsize = inf.BLOCK_SIZE-inf.CAPITOL_SPACING
        sl = random.sample(xrange(bsize**2), 300)
        for l in sl:
            pos = Vect(l % bsize + inf.CAPITOL_SPACING // 2,
                       l // bsize + inf.CAPITOL_SPACING // 2)
            tiles = [self.getTileType(pos),
                     self.getTileType(inf.tileDirMove(pos, 2)),
                     self.getTileType(inf.tileDirMove(pos, 3)),
                     self.getTileType(inf.tileDirMove(pos, 4))]
            # Ensure enough surrounding blocks are land.
            if len(filter(inf.isGoodStartType, tiles)) == 4:
                # Check distance to all buildables.
                clear = True
                if blist:
                    for b in blist:
                        if pos.distanceTo(b.pos) < inf.CAPITOL_SPACING:
                            clear = False
                            break
                if clear == True:
                    d = random.sample([BuildType.topVertex, BuildType.bottomVertex], 1)
                    return (Vect(self._pos.x, self._pos.y), Vect(pos.x, pos.y, d[0]))
        bb.atomicSetFullOfCapitols()
        return None

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
        if d == 1:
            out.y -= 1
        elif d == 4:
            out.y += 1
        else:
            if d == 0 or d == 5:
                out.x += 1
            elif d == 2 or d == 3:
                out.x -= 1
        if (coord.x % 2 == 0) and (d == 0 or d == 2):
            out.y -= 1
        elif coord.x % 2 and (d == 3 or d == 5):
            out.y += 1
        return out

    def _sumLand(self, coord, surrounding_blocks=None):
        """Sum the number of land tiles around the given tile coord."""
        sum = 0
        t = TileType.water
        n = Vect(0, 0)
        for i in xrange(6):
            self._getNeighbor(coord, i, n)
            if (n.x < inf.BLOCK_SIZE and n.x >= 0 and n.y < inf.BLOCK_SIZE and
                n.y >= 0):
                t = self.fastGetTileType(n.x, n.y)
            elif not surrounding_blocks:
                t = TileType.water
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
            if t != TileType.water:
                sum += 1
        return sum

    def _generateTile(self, coord, surrounding_blocks, probabilities):
        """Generate a random tile, taking surrounding tiles into account."""
        sum = self._sumLand(coord, surrounding_blocks)
        t = self.get(coord)
        # Land tile.
        if random.randint(0, 99) < probabilities[sum]:
            t.randomize()
        self.set(coord, t)
