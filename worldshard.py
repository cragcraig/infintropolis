from google.appengine.api import memcache

import algorithms
import inf
import mapblock
from inf import Vect, TileType
from buildable import Buildable
from mapblock import MapBlock


class WorldShard:
    """Abstracts and optimizes operations involving multiple MapBlocks."""
    _toload = set()
    _core = set()
    _mapblocks = dict()

    def addBlock(self, vect):
        """Adds a block and its dependencies to the shard."""
        self._toload.update(vect.getSurroundingBlocks()) 
        self._core.add(Vect(vect.x, vect.y))

    def loadDependencies(self):
        """Loads all dependencies for this shard."""
        self._loadCachedBlocks()
        self._loadDbBlocks()
        # Generate non-existent core MapBlocks.
        for n in self._toload:
            if n in self._core:
                m = MapBlock(n, load=False)
                m.generate()
                self._mapblocks[n] = m

    def _loadCachedBlocks(self):
        """Attempts to load shard dependencies from memcache.
        
        Removes successfully loaded blocks from self._toload.
        """
        vects = list(self._toload)
        keys = map(mapblock.genCacheKey, vects)
        models = memcache.get_multi(keys)
        for n in models.values():
            if n:
                v = Vect(n.x, n.y)
                m = MapBlock(v, load=False)
                m.setModel(n)
                self._mapblocks[v] = m
                self._toload.discard(v)


    def _loadDbBlocks(self):
        """Attempts to load shard dependencies from the database.
        
        Removes successfully loaded blocks from self._toload.
        """
        vects = list(self._toload)
        keys = map(mapblock.genKey, vects)
        models = mapblock.BlockModel.get_by_key_name(keys)
        for n in zip(vects, models):
            if n[1]:
                m = MapBlock(n[0], load=False)
                m.setModel(n[1])
                m.cache()
                self._mapblocks[n[0]] = m
                self._toload.discard(n[0])

    def applyLOS(self, nationName):
        """Generates line of sight data for all blocks."""
        for m in self._mapblocks:
            m.initLOS()
        for m in self._mapblocks:
            blist = m.getBuildablesList()
            for b in blist:
                if b.nationName == nationName:
                    for v in b.getSurroundingTiles():
                        self._recurseLOS(v, m, BuildType.LOSVision[b.level])

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
        newcount = count - TileType.LOSCost[tiles[index]]
        if newcount <= 0:
            return
        for p in inf.listSurroundingTilePos(pos):
            v = Vect(p[0], p[1])
            if 0 <= v.x < inf.BLOCK_SIZE and 0 <= v.y <= inf.BLOCK_SIZE:
                self._recurseLOS(v, block, newcount)
                continue
            else:
                bv = Vect(block._pos.x, block._pos.y)
                if v.x < 0:
                    bv.x -= 1
                    v.x += inf.BLOCK_SIZE
                elif v.x >= inf.BLOCK_SIZE:
                    bv.x += 1
                    v.x -= inf.BLOCK_SIZE
                if v.y < 0:
                    bv.y -= 1
                    v.y += inf.BLOCK_SIZE
                elif v.y >= inf.BLOCK_SIZE:
                    bv.y += 1
                    v.y -= inf.BLOCK_SIZE
                if bv in self._mapblocks:
                    self._recurseLOS(v, self._mapblocks[bv], newcount)

    def getJSONDict(self):
        """Return a JSON dictionary for the core MapBlocks."""
        r = {}
        for v in self._core:
            jId = v.getBlockJSONId()
            r[jId] = " "
            if v not in self._mapblocks:
                continue
            block = self._mapblocks[v]
            if block.exists():
                r[jId] = {
                    'mapblock': block.getString(),
                    'buildableblock': block.getBuildablesJSON()}
        return r
