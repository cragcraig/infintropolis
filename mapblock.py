import random
import pickle

from google.appengine.ext import db
from google.appengine.api import memcache

import inf
import buildable
import algorithms
from inf import Vect, Tile, TileType

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
    x = db.IntegerProperty(required=True, indexed=False)
    y = db.IntegerProperty(required=True, indexed=False)
    token = db.IntegerProperty(indexed=False)
    # MapBlock
    tiletype = db.ListProperty(int, indexed=False)
    roll = db.ListProperty(int, indexed=False)
    # BuildableBlock
    count = db.IntegerProperty(indexed=False)
    isFullOfCapitols = db.BooleanProperty(indexed=True)
    hasBuilding = db.BooleanProperty(indexed=True)
    buildables = db.ListProperty(db.Blob, indexed=False)


class SurroundingMapBlocks:
    """Nearbly map tile blocks.
    
    Used when generating a map. Will not generate map blocks if they do not
    already exist.
    """

    def __init__(self, pos, worldshard=None):
        self.north = None
        self.south = None
        self.west = None
        self.east = None
        vn = Vect(pos.x, pos.y - 1)
        vs = Vect(pos.x, pos.y + 1)
        vw = Vect(pos.x - 1, pos.y)
        ve = Vect(pos.x + 1, pos.y)
        # Get preloaded MapBlocks from WorldShard.
        if worldshard:
            self.north = worldshard.getBlockOnly(vn)
            self.south = worldshard.getBlockOnly(vs)
            self.west = worldshard.getBlockOnly(vw)
            self.east = worldshard.getBlockOnly(ve)
        # Load unloaded MapBlocks.
        else:
            if not self.north:
                self.north = MapBlock(vn, generate_nonexist=False)
                if not self.north.exists():
                    self.north = None
            if not self.south:
                self.south = MapBlock(vs, generate_nonexist=False)
                if not self.south.exists():
                    self.south = None
            if not self.west:
                self.west = MapBlock(vw, generate_nonexist=False)
                if not self.west.exists():
                    self.west = None
            if not self.east:
                self.east = MapBlock(ve, generate_nonexist=False)
                if not self.east.exists():
                    self.east = None


class MapBlock(inf.DatabaseObject):
    """A block of map tiles."""
    modelClass = BlockModel

    def __init__(self, pos, load=True, generate_nonexist=True, worldshard=None):
        """Load BlockModel from cache/database.

        By default a BlockModel will be generated and stored to the database
        if one does not exist.
        """
        inf.DatabaseObject.__init__(self)
        self._pos = pos.copy()
        self.worldshard = worldshard
        self._buildableslist = None
        self.los = None
        self.costmap = None
        if load:
            self.load()
            if not self.exists() and generate_nonexist:
                self.generate()
            if self.worldshard:
                self.worldshard.addBlockData(self)

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
            f = (t == len(prob_map) - 1)
            for j in xrange(inf.BLOCK_SIZE):
                i -= 1
                for k in xrange(j, i):
                    self._generateTile(Vect(j, k), surrounding, prob_map[t], f)
                for k in xrange(j, i):
                    self._generateTile(Vect(k, i), surrounding, prob_map[t], f)
                for k in xrange(i, j, -1):
                    self._generateTile(Vect(i, k), surrounding, prob_map[t], f)
                for k in xrange(i, j, -1):
                    self._generateTile(Vect(k, j), surrounding, prob_map[t], f)
        tk = random.randint(1, 90000000)
        self.loadOrCreate(x=self._pos.x, y=self._pos.y, token=tk,
                          tiletype=self._model.tiletype,
                          roll=self._model.roll, count=0,
                          isFullOfCapitols=False, hasBuilding=False,
                          buildables=[])

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
        sl = random.sample(xrange(bsize**2), 300)
        for l in sl:
            pos = Vect(l % bsize + inf.CAPITOL_SPACING // 2,
                       l // bsize + inf.CAPITOL_SPACING // 2)
            tiles = [self.getTileType(pos),
                     self.getTileType(inf.tileDirMove(pos, 2)),
                     self.getTileType(inf.tileDirMove(pos, 3)),
                     self.getTileType(inf.tileDirMove(pos, 4))]
            # Ensure enough surrounding blocks are land.
            if len(filter(inf.isGoodStartType, tiles)) >= 3:
                # Check distance to all buildables.
                clear = True
                if blist:
                    for b in blist:
                        if pos.distanceTo(b.pos) < inf.CAPITOL_SPACING:
                            clear = False
                            break
                if clear == True:
                    d = random.sample([buildable.BuildType.topVertex,
                                       buildable.BuildType.bottomVertex], 1)
                    return inf.WorldVect(Vect(self._pos.x, self._pos.y),
                                         Vect(pos.x, pos.y, d[0]))
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
                  surrounding_blocks.west):
                t = surrounding_blocks.west.fastGetTileType(
                    x + inf.BLOCK_SIZE, y)
            elif (x >= inf.BLOCK_SIZE and y < inf.BLOCK_SIZE and
                  y >= 0 and surrounding_blocks.east):
                t = surrounding_blocks.east.fastGetTileType(
                    x - inf.BLOCK_SIZE, y)
            elif (y < 0 and x < inf.BLOCK_SIZE and x >= 0 and
                  surrounding_blocks.north):
                t = surrounding_blocks.north.fastGetTileType(
                    x, y + inf.BLOCK_SIZE)
            elif (y >= inf.BLOCK_SIZE and x < inf.BLOCK_SIZE and
                  x >= 0 and surrounding_blocks.south):
                t = surrounding_blocks.south.fastGetTileType(
                    x, y - inf.BLOCK_SIZE)
            else:
                t = TileType.water
            if t != TileType.water:
                sum += 1
        return sum

    def _generateTile(self, coord, surrounding_blocks, probabilities, final):
        """Generate a random tile, taking surrounding tiles into account."""
        sum = self._sumLand(coord, surrounding_blocks)
        t = self.get(coord)
        # Land tile.
        if random.randint(0, 99) < probabilities[sum]:
            t.randomize()
        if final and sum == 0:
            t.setWater()
        self.set(coord, t)

    def atomicBuild(self, buildable):
        """Builds the buildable in an atomic database transaction."""
        if not self.worldshard:
            return False
        if db.run_in_transaction(MapBlock._build, self, buildable):
            self.cache()
            return True
        else:
            self.load()
            return False

    def atomicBuildCost(self, buildable, capitol):
        """Builds the buildable in an atomic database XG transaction.
        
        Removes cost resources from the Capitol. If they are not avaliable the
        build will fail.
        """
        if not self.worldshard:
            return False
        xg_on = db.create_transaction_options(xg=True)
        if db.run_in_transaction_options(xg_on, MapBlock._buildcost,
                                         self, buildable, capitol):
            self.cache()
            capitol.cache()
            return True
        else:
            self.load()
            capitol.load()
            return False

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
 
    def getBuildablesList(self, refresh=False):
        """Get a list of buildables."""
        if not self._buildableslist or refresh:
            self._buildableslist =\
                [buildable.unserialize(b, self._pos)
                 for b in self._model.buildables]
        return self._buildableslist

    def getBuildable(self, pos, nation=None, capitol=None, bclass=None):
        """Returns the buildable located at pos, if one exists.

        Any provided nation or class attributes will be enforced.
        """
        for b in self.getBuildablesList():
            if b.pos == pos and (not nation or b.nationName == nation) and\
               (bclass == None or isinstance(b, bclass)) and\
               (capitol == None or b.capitolNum == capitol):
                return b
        return None

    def hasBuildableAt(self, pos, nation=None, capitol=None, bclass=None):
        """Checks if there is a buildable at the given location.

        Any provided nation or class attributes will be enforced.
        """
        for b in self.getBuildablesList():
            if b.pos == pos and (not nation or b.nationName == nation) and\
               (bclass == None or isinstance(b, bclass)) and\
               (capitol == None or b.capitolNum == capitol):
                return True
        return False

    def _build(self, buildable, put=True):
        """Builds the buildable. For use inside atomicBuild()."""
        self.dbGet()
        self.worldshard.clear()
        self.worldshard.addBlockData(self)
        if buildable.checkBuild(self.worldshard) and self.exists():
            self._delBuildable(buildable.pos)
            self._addBuildable(buildable)
            if put:
                self.put()
            return True
        return False

    def _buildcost(self, buildable, capitol):
        """Builds the buildable. For use inside atomicBuildCost()."""
        if not capitol.addResources(buildable.getCost()):
            return False
        if not self._build(buildable):
            return False
        return True

    def _addBuildable(self, buildable):
        """Adds a buildable to the internal list."""
        self._model.count += 1
        self._model.buildables.append(db.Blob(buildable.serialize()))
        if buildable.getGather() > 0:
            self._model.hasBuilding = True
        self._buildableslist = None

    def _delBuildable(self, pos):
        """Removes a buildable from the internal list."""
        i = 0
        for b in self._model.buildables:
            l = pickle.loads(b)
            if Vect(l[1], l[2], l[3]) == pos:
                break
            i += 1
        if i < len(self._model.buildables):
            del self._model.buildables[i]
            self._model.count -= 1
        self._buildableslist = None

    def getBuildablesJSON(self):
        """Construct a list of dictionary representations of buildables."""
        l = self.getBuildablesList()
        return [b.getJSONDict() for b in l]

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


def genKey(blockVect):
    """Generates a db key for a mapblock."""
    return 'mapblock:' + str(blockVect.x) + ',' + str(blockVect.y)

def genCacheKey(blockVect):
    """Generates a memcache key for a mapblock."""
    return inf.getCachePrefix() + genKey(blockVect)
