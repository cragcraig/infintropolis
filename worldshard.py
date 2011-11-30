from google.appengine.ext import db
from google.appengine.api import memcache

import inf
import mapblock
from inf import Vect, TileType, Tile
from buildable import Buildable, BuildType
from mapblock import MapBlock


class WorldShard:
    """Abstracts and optimizes operations involving multiple MapBlocks."""
    _maxsize = 1024

    def __init__(self):
        self._toload = set()
        self._core = set()
        self._mapblocks = dict()

    def addBlock(self, vect):
        """Adds a block and its dependencies to the shard."""
        for v in vect.getSurroundingBlocksAndSelf():
            if v not in self._mapblocks:
                self._toload.add(v)
        self._core.add(Vect(vect.x, vect.y))

    def addSurroundingBlocks(self, vect):
        """Adds a block's dependencies to the shard."""
        for v in vect.getSurroundingBlocks():
            if v not in self._mapblocks:
                self._toload.add(v)

    def addSingleBlock(self, vect):
        """Adds a block to the shard."""
        self._toload.add(Vect(vect.x, vect.y))
        self._core.add(Vect(vect.x, vect.y))

    def loadBlock(self, vect, isCore=True):
        """Adds a block to the shard, loading immediately."""
        v = Vect(vect.x, vect.y)
        self._toload.add(v)
        if isCore:
            self._core.add(v)
        self.loadDependencies(generate=isCore)
        if v in self._mapblocks:
            return self._mapblocks[v]
        return None

    def addBlockData(self, mapblock):
        """Adds a block with associated MapBlock data directly."""
        v = mapblock.getPos()
        self._toload.discard(v)
        self._core.add(v)
        self._mapblocks[v] = mapblock

    def clear(self):
        """Clears all data in the shard."""
        self._toload = set()
        self._core = set()
        self._mapblocks = dict()

    def getBlock(self, vect, isCore=True):
        """Returns a block if it is in the shard, loading it otherwise."""
        if vect in self._mapblocks:
            r = self._mapblocks[vect]
            #r.worldshard = self
        else:
            self.guillotineSize()
            r = self.loadBlock(vect, isCore=isCore)
        if not r or not r.exists():
            return None
        return r

    def getBlockOnly(self, vect):
        """Returns a block if it is already loaded in the shard."""
        if vect in self._mapblocks:
            r = self._mapblocks[vect]
            if not r.exists():
                return None
            return r
        return None

    def guillotineSize(self):
        """Reduce the stored MapBlocks to no more than WorldShard._maxsize."""
        if len(self._mapblocks) > WorldShard._maxsize:
            d = random.sample(self._mapblocks,
                              len(self._mapblocks) - WorldShard._maxsize)
            for k in d:
                del self._mapblocks[k]

    def checkBuildableRequirements(self, blockPos, buildPos, truelist,
                                   falselist, requireLand=False,
                                   requireWater=False):
        """Check a list of buildable requirements."""
        istrue = False
        # Check truelist.
        for i in truelist:
            if self.hasBuildableAt(blockPos,
                                   inf.tileDirMove(buildPos, i[0]), *i[1:]):
                istrue = True
                break
        if not istrue:
            return False
        # Check falselist.
        for i in falselist:
            if self.hasBuildableAt(blockPos,
                                   inf.tileDirMove(buildPos, i[0]), *i[1:]):
                return False
        # Check tile type requirements.
        if requireLand and not self._checkForTile(blockPos, buildPos,
                                                  Tile.isLand):
            return False
        if requireWater and not self._checkForTile(blockPos, buildPos,
                                                   Tile.isWater):
            return False
        return True

    def hasBuildableAt(self, blockPos, pos, d, nation=None, capitol=None,
                       bclass=None):
        """Checks if there is a buildable at the given location.

        Any provided nation or class attributes will be enforced. Only x,y are
        used from the pos Vect as d is a separate parameter to the method.
        Wrapping of the pos vector and subsequent use of the corrected blockPos
        is performed automatically.
        """
        p = pos.copy()
        p.d = d
        bp = blockPos.copy()
        inf.wrapCoordinates(bp, p)
        if bp not in self._mapblocks:
            self.loadBlock(bp, isCore=False)
        if bp not in self._mapblocks:
            return False
        return self._mapblocks[bp].hasBuildableAt(p, nation, capitol, bclass)

    def _checkForTile(self, blockPos, buildPos, tileMethod):
        """True if tileMethod evaluates True for a tile adjacent to buildPos."""
        for v in buildPos.getSurroundingTiles():
            t = self.getTile(blockPos, v)
            if t and tileMethod(t):
                return True
        return False

    def getTile(self, blockPos, pos, isCore=False):
        """Returns the Tile at the specificed location."""
        bp, p = inf.getWrappedCoordinates(blockPos, pos)
        b = self.getBlock(bp, isCore=isCore)
        if b:
            return b.get(p)
        return None

    def cacheCore(self):
        """Cache all core blocks."""
        for v in self._core:
            m = self._mapblocks[v]
            if m.exists():
                m.cache()

    def atomicPathBuildable(self, nation, path):
        """Move a buildable along a path."""
        xg_on = db.create_transaction_options(xg=True)
        if db.run_in_transaction_options(xg_on, WorldShard._atomicPath,
                                         self, nation, path):
            self.cacheCore()
            return True
        else:
            self.clear()
            return False

    def _atomicPath(self, nation, path, enforceContinuous=True):
        """Intended only for internal use by atomicPathBuildable."""
        # Load blocks and add to worldshard.
        for bv in path:
            self.addSingleBlock(bv.block)
        self.loadDependencies(generate=False, useCached=False)

        origin = path.pop(0)
        dest = origin

        # Check path.
        pbv = origin
        for bv in path:
            b = self.getBlockOnly(bv.block)
            if b.hasBuildableAt(bv.pos) or b.get(bv.pos).isLand() or\
               (enforceContinuous and not bv.isAdjacent(pbv)):
                break
            pbv = bv
            dest = bv

        # Select origin and dest blocks.
        oBlock = self.getBlockOnly(origin.block)
        dBlock = self.getBlockOnly(dest.block)
        if not oBlock or not dBlock:
            return False

        # Move buildable.
        b = oBlock.getBuildable(origin.pos, nation=nation.getName())
        if not b or not b.canMove():
            return False
        b.pos = dest.pos
        oBlock._delBuildable(origin.pos)
        dBlock._addBuildable(b)

        # Save.
        if origin.block == dest.block:
            oBlock.put()
        else:
            db.put([oBlock._model, dBlock._model])
        return True

    def loadDependencies(self, generate=True, useCached=True):
        """Loads all dependencies for this shard."""
        if useCached:
            self._loadCachedBlocks()
        self._loadDbBlocks()
        # Generate non-existent core MapBlocks.
        if generate:
            for n in self._toload:
                if n in self._core and n not in self._mapblocks:
                    m = MapBlock(n, load=False, worldshard=self)
                    self._mapblocks[n] = m
                    m.generate(self)
        self._toload = set()

    def _loadCachedBlocks(self):
        """Attempts to load shard dependencies from memcache.
        
        Removes successfully loaded blocks from self._toload.
        """
        vects = list(self._toload)
        if not len(vects):
            return
        keys = map(mapblock.genCacheKey, vects)
        models = memcache.get_multi(keys)
        for n in models.values():
            if n:
                v = Vect(n.x, n.y)
                m = MapBlock(v, load=False, worldshard=self)
                m.setModel(n)
                self._mapblocks[v] = m
                self._toload.discard(v)

    def _loadDbBlocks(self):
        """Attempts to load shard dependencies from the database.
        
        Removes successfully loaded blocks from self._toload.
        """
        vects = list(self._toload)
        if not len(vects):
            return
        keys = map(mapblock.genKey, vects)
        models = mapblock.BlockModel.get_by_key_name(keys)
        for n in zip(vects, models):
            if n[1]:
                m = MapBlock(n[0], load=False, worldshard=self)
                m.setModel(n[1])
                m.cache()
                self._mapblocks[n[0]] = m
                self._toload.discard(n[0])

    def applyLOS(self, nationName):
        """Generates line of sight data for all blocks."""
        for m in self._mapblocks.values():
            m.initLOS()
        for m in self._mapblocks.values():
            blist = m.getBuildablesList()
            for b in blist:
                if b.nationName == nationName:
                    for v in b.pos.getSurroundingTiles():
                        self._recurseLOS(v, m, b.getVision())

    def _recurseLOS(self, pos, block, count):
        """Recursively performs line of sight calculations.

        pos: Current pos in block as a Vert().
        block: Current MapBlock.
        count: Current LOS count.
        """
        index = pos.getListPos()
        if block.costmap[index] >= count:
            return
        block.los[index] = 1
        block.costmap[index] = count
        newcount = count - TileType.LOSCost[block._model.tiletype[index]]
        if newcount <= 0:
            return
        for p in inf.listSurroundingTilePos(pos):
            v = Vect(p[0], p[1])
            if 0 <= v.x < inf.BLOCK_SIZE and 0 <= v.y < inf.BLOCK_SIZE:
                self._recurseLOS(v, block, newcount)
                continue
            else:
                bv = Vect(block._pos.x, block._pos.y)
                inf.wrapCoordinates(bv, v)
                if bv in self._mapblocks:
                    self._recurseLOS(v, self._mapblocks[bv], newcount)

    def getJSONDict(self):
        """Return a JSON dictionary for the core MapBlocks."""
        r = {}
        for v in self._core:
            if v not in self._mapblocks:
                continue
            block = self._mapblocks[v]
            if block.exists():
                r[v.getBlockJSONId()] = {
                    'mapblock': block.getString(),
                    'buildableblock': block.getBuildablesJSON(),
                    'token': block.getToken()}
        return r

    def getJSONBuildablesDict(self):
        """Return a JSON dictionary for the core MapBlocks."""
        r = {}
        for v in self._core:
            if v not in self._mapblocks:
                continue
            block = self._mapblocks[v]
            if block.exists():
                r[v.getBlockJSONId()] = {
                    'buildableblock': block.getBuildablesJSON()}
        return r
