import random

from google.appengine.ext import db
from google.appengine.api import memcache

import inf
import algorithms
from inf import Vect, Tile, TileType
from buildable import Buildable, BuildType

# Probabilities for map generator.
PROBABILITY_MAP = [[3, 40, 30, 10, 30, 80, 90],
                   [0, 0, 50, 75, 85, 95, 80],
                   [0, 20, 0, 0, 0, 0, 100]]
# SMALL ISLANDS
#PROBABILITY_MAP = [[3, 30, 10, 10, 30, 80, 90],
#                   [0, 0, 50, 75, 85, 95, 80],
#                   [0, 20, 0, 0, 0, 0, 100]]

BUILDABLE_LIST_SIZE = 8


class BlockModel(db.Model):
    """A database model representing a 50x50 block of tiles."""
    x = db.IntegerProperty(required=True, indexed=True)
    y = db.IntegerProperty(required=True, indexed=False)
    token = db.IntegerProperty(indexed=False)
    # MapBlock
    tiletype = db.ListProperty(int, indexed=False)
    roll = db.ListProperty(int, indexed=False)
    # BuildableBlock
    count = db.IntegerProperty(indexed=True)
    isFullOfCapitols = db.BooleanProperty(indexed=True)
    buildables = db.ListProperty(int, indexed=False)
    nations = db.StringListProperty(indexed=False)

class SurroundingMapBlocks:
    """Nearbly map tile blocks.
    
    Used when generating a map. Will not generate map blocks if they do not
    already exist.
    """
    north = None
    south = None
    west = None
    east = None

    def __init__(self, pos, worldshard=None):
        vn = Vect(pos.x, pos.y - 1)
        vs = Vect(pos.x, pos.y + 1)
        vw = Vect(pos.x - 1, pos.y)
        ve = Vect(pos.x + 1, pos.y)
        # Get preloaded MapBlocks from WorldShard.
        if worldshard:
            if vn in worldshard._mapblocks:
                self.north = worldshard._mapblocks[vn]
            if vs in worldshard._mapblocks:
                self.south = worldshard._mapblocks[vs]
            if vw in worldshard._mapblocks:
                self.west = worldshard._mapblocks[vw]
            if ve in worldshard._mapblocks:
                self.east = worldshard._mapblocks[ve]
        # Load unloaded MapBlocks.
        if not self.north:
            self.north = MapBlock(vn, generate_nonexist=False)
        if not self.south:
            self.south = MapBlock(vs, generate_nonexist=False)
        if not self.west:
            self.west = MapBlock(vw, generate_nonexist=False)
        if not self.east:
            self.east = MapBlock(ve, generate_nonexist=False)


class MapBlock(inf.DatabaseObject):
    """A block of map tiles."""
    modelClass = BlockModel
    _pos = Vect(0,0)
    los = None
    costmap = None

    def __init__(self, pos, load=True, generate_nonexist=True):
        """Load BlockModel from cache/database.

        By default a BlockModel will be generated and stored to the database
        if one does not exist.
        """
        self._pos = pos.copy()
        if load:
            self.load()
            if not self.exists() and generate_nonexist:
                self.generate()

    def initLOS(self):
        """Create data structures required for LOS."""
        self.los = (inf.BLOCK_SIZE * inf.BLOCK_SIZE) * [0]
        self.costmap = (inf.BLOCK_SIZE * inf.BLOCK_SIZE) * [0]

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

    def generate(self, worldshard=None):
        """Randomly generate the MapBlock."""
        prob_map = PROBABILITY_MAP
        self._model = BlockModel(x=self._pos.x, y=self._pos.y)
        self._clear()
        surrounding = SurroundingMapBlocks(self._pos, worldshard)
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
        tk = random.randint(1, 90000000)
        self.loadOrCreate(x=self._pos.x, y=self._pos.y, token=tk,
                          tiletype=self._model.tiletype,
                          roll=self._model.roll, count=0,
                          isFullOfCapitols=False, buildables=[], nations=[])

    def getString(self):
        """Construct a comma deliminated string MapBlock representation."""
        return ''.join([str(int(self._model.tiletype[i])) + ':' +
                        (str(int(self._model.roll[i])) + ','
                         if self.los[i] else "-1,")
                        for i in xrange(inf.BLOCK_SIZE * inf.BLOCK_SIZE)])

    def getKeyName(self):
        return genKey(self._pos)

    def findOpenSpace(self):
        """Find an open space for a new capitol, if possible.
        
        Returns either None or a tuple (Vect(block), Vect(pos)).
        """
        blist = self.getBuildablesList()
        bsize = inf.BLOCK_SIZE-inf.CAPITOL_SPACING
        sl = random.sample(xrange(bsize**2), 1000)
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

    def _sumLand(self, coord, surrounding_blocks=None):
        """Sum the number of land tiles around the given tile coord."""
        sum = 0
        t = TileType.water
        x = None
        y = None
        for p in inf.listSurroundingTilePos(coord):
            x = p[0]
            y = p[1]
            if (x < inf.BLOCK_SIZE and x >= 0 and y < inf.BLOCK_SIZE and
                y >= 0):
                t = self.fastGetTileType(x, y)
            elif not surrounding_blocks:
                t = TileType.water
            elif (x < 0 and y < inf.BLOCK_SIZE and y >= 0 and
                  surrounding_blocks.west.exists()):
                t = surrounding_blocks.west.fastGetTileType(
                    x + inf.BLOCK_SIZE, y)
            elif (x >= inf.BLOCK_SIZE and y < inf.BLOCK_SIZE and
                  y >= 0 and surrounding_blocks.east.exists()):
                t = surrounding_blocks.east.fastGetTileType(
                    x - inf.BLOCK_SIZE, y)
            elif (y < 0 and x < inf.BLOCK_SIZE and x >= 0 and
                  surrounding_blocks.north.exists()):
                t = surrounding_blocks.north.fastGetTileType(
                    x, y + inf.BLOCK_SIZE)
            elif (y >= inf.BLOCK_SIZE and x < inf.BLOCK_SIZE and
                  x >= 0 and surrounding_blocks.south.exists()):
                t = surrounding_blocks.south.fastGetTileType(
                    x, y - inf.BLOCK_SIZE)
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

    def atomicBuild(self, buildable, colors):
        """Builds the buildable in an atomic database transaction."""
        if db.run_in_transaction(MapBlock._build, self, buildable,
                                 colors):
            self.cache()
        else:
            self.load()

    def atomicSetFullOfCapitols(self):
        """Builds the buildable in an atomic database transaction."""
        if db.run_in_transaction(MapBlock._setFull, self):
            self.cache()
        else:
            self.load()

    def _setFull(self):
        """Set full of capitols."""
        self.dbGet()
        self._model.isFullOfCapitols = True
        self.put()
        return True
 
    def getBuildablesList(self):
        return [Buildable(Vect(self._model.buildables[i],
                               self._model.buildables[i+1],
                               self._model.buildables[i+2]),
                          self._model.buildables[i+3],
                          self._model.nations[self._model.buildables[i+6]],
                          self._model.buildables[i+7])
                for i in xrange(0, len(self._model.buildables),
                                BUILDABLE_LIST_SIZE)]

    def _build(self, buildable, colors):
        """Builds the buildable. For use inside atomicBuild()."""
        self.dbGet()
        self._addBuildable(buildable, colors)
        self.put()
        return True

    def _addBuildable(self, buildable, colors):
        """Adds a buildable to the internal list."""
        nationIndex = self._getNationIndex(buildable.nationName)
        assert len(colors) == 2
        self._model.count += 1
        self._model.buildables.extend(buildable.getList())
        self._model.buildables.extend(colors)
        self._model.buildables.extend([int(nationIndex), int(buildable.capitolNum)])

    def _delBuildable(self, pos):
        """Removes a buildable from the internal list."""
        p = pos.getList()
        lp = len(p)
        for i in xrange(0, len(self._model.buildables), BUILDABLE_LIST_SIZE):
            if self._model.buildables[i:i+lp] == p:
                del self._model.buildables[i:i+BUILDABLE_LIST_SIZE]
                self._model.count -= 1
                break

    def getBuildablesJSON(self):
        """Construct a list of dictionary representations of buildables."""
        return [{'x': int(self._model.buildables[i]),
                 'y': int(self._model.buildables[i+1]),
                 'd': BuildType.dToJSON[self._model.buildables[i+2]],
                 't': BuildType.tToJSON[self._model.buildables[i+3]],
                 'c1': self._int2hexcolor(self._model.buildables[i+4]),
                 'c2': self._int2hexcolor(self._model.buildables[i+5]),
                 'n': self._model.nations[self._model.buildables[i+6]],
                 'i': int(self._model.buildables[i+7])}
                for i in xrange(0, len(self._model.buildables),
                                BUILDABLE_LIST_SIZE)]

    def getToken(self):
        """Return the MapBlock token required for Buildables-only requests.
        
        Returns 0 if none of the MapBlock is within calculated LOS.
        """
        if not self.los or not any(self.los):
            return 0
        else:
            return self._model.token

    def checkToken(self, token):
        """Returns True if the token matches the MapBlock token."""
        return token == self._model.token

    def _getNationIndex(self, nationName):
        """Get the index of a nation in the model's nation list.

        Adds the nation if it does not exist. It is up to you to save the
        updated model to the database.
        """
        if nationName not in self._model.nations:
            self._model.nations.append(nationName)
        return self._model.nations.index(nationName)

    def _int2hexcolor(self, color):
        return "%06x" % color


def genKey(blockVect):
    """Generates a db key for a mapblock."""
    return 'mapblock:' + str(blockVect.x) + ',' + str(blockVect.y)

def genCacheKey(blockVect):
    """Generates a memcache key for a mapblock."""
    return inf.getCachePrefix() + genKey(blockVect)
