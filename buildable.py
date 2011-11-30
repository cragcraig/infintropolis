import copy
import pickle

import inf


def unserialize(str, block):
    """Recreate a serialized buildable."""
    b = pickle.loads(str)
    return _create(b[0], block, inf.Vect(b[1], b[2], b[3]), *b[4:])


def new(JSONBuildableType, *args, **kwargs):
    """Create a buildable object of the specified JSON type."""
    f = filter(lambda o: o.classId == JSONBuildableType,
               BuildType.objects)
    assert len(f) == 1
    return f[0](*args, **kwargs)


def _create(buildableType, *args, **kwargs):
    """Create a buildable object of the specified serialized type."""
    obj = BuildType.objects[buildableType]
    return obj(*args, **kwargs)


class Buildable:
    """Represents an buildable game object. Should never be used directly.

    Edge
    d = {t, c, b}
     t  /\ 
    c  |  |
     b  \/

    Vertex
    d = {t, b}
     t ./\ 
       |  |
     b '\/
    """

    def __init__(self, blockPos, pos, nationName=None, capitolNum=None,
                 colors=(0,0), validate=True):
        self.pos = pos.copy()
        self.block = blockPos.copy()
        self.nationName = nationName
        self.capitolNum = capitolNum
        self.validate = validate
        self.colors = colors

    def build(self, shard, nation, capitol):
        """Adds this buildable in all necessary database models."""
        self.nationName = nation.getName()
        self.capitolNum = capitol.getNumber()
        self.colors = nation.getColors()
        block = shard.getBlock(self.block)
        if block and (not self.validate or self.checkBuild(shard)):
            block.atomicBuildCost(self, capitol)

    def gather(self, shard, roll, resources):
        """Add resources gathered for this roll to the resource list."""
        if self.getGather() == 0:
            return
        for v in self.pos.getSurroundingTiles():
            t = shard.getTile(self.block, v)
            if t and t.roll == roll:
                i = inf.TileType.typeToResource[t.tiletype]
                if i is not None:
                    resources[i] += self.getGather()

    def getGather(self):
        """Returns the number of resources gathered in a single event."""
        return 0
               
    def getCost(self):
        """Returns the cost of this buildable as a list."""
        return [0, 0, 0, 0, 0, 0]

    def getVision(self):
        return 1

    def checkBuild(self, shard):
        """Checks if this buildable can be built."""
        # Perform type-specific validation.
        return False

    def _checkBuildShip(self, shard):
        """Check if this buildable can be built as a ship."""
        if not self.pos.isMiddle():
            return False
        wtile = shard.getTile(self.block, self.pos)
        return wtile and wtile.isWater() and\
               shard.checkBuildableRequirements(self.block, self.pos,
                ((-1, BuildType.topVertex, self.nationName, self.capitolNum,
                  Port),
                 (-1, BuildType.bottomVertex, self.nationName, self.capitolNum,
                  Port),
                 (0, BuildType.topVertex, self.nationName, self.capitolNum,
                  Port),
                 (0, BuildType.bottomVertex, self.nationName, self.capitolNum,
                  Port),
                 (1, BuildType.bottomVertex, self.nationName, self.capitolNum,
                  Port),
                 (5, BuildType.topVertex, self.nationName, self.capitolNum,
                  Port)),
                ((-1, BuildType.middle),))

    def _checkBuildVertex(self, shard, requireWater=False):
        if not self.pos.isVertex():
            return False
        """Check if this buildable can be built at a vertex."""
        if self.pos.d == BuildType.topVertex:
            return shard.checkBuildableRequirements(self.block, self.pos,
                ((-1, BuildType.centerEdge, self.nationName, self.capitolNum),
                 (-1, BuildType.topEdge, self.nationName, self.capitolNum),
                 (2, BuildType.bottomEdge, self.nationName, self.capitolNum)),
                ((-1, BuildType.topVertex),
                 (-1, BuildType.bottomVertex),
                 (1, BuildType.bottomVertex),
                 (2, BuildType.bottomVertex)),
                 requireLand=True, requireWater=requireWater)
        elif self.pos.d == BuildType.bottomVertex:
            return shard.checkBuildableRequirements(self.block, self.pos,
                ((-1, BuildType.centerEdge, self.nationName, self.capitolNum),
                 (-1, BuildType.bottomEdge, self.nationName, self.capitolNum),
                 (4, BuildType.topEdge, self.nationName, self.capitolNum)),
                ((-1, BuildType.topVertex),
                 (-1, BuildType.bottomVertex),
                 (4, BuildType.topVertex),
                 (5, BuildType.topVertex)),
                 requireLand=True, requireWater=requireWater)
        else:
            return False

    def _checkBuildEdge(self, shard, bclass, rland, rwater):
        """Check if this buildable can be built at an edge."""
        if not self.pos.isEdge():
            return False
        # Perform verification.
        if self.pos.d == BuildType.topEdge:
            return shard.checkBuildableRequirements(self.block, self.pos,
                ((-1, BuildType.topVertex, self.nationName, self.capitolNum),
                 (1, BuildType.bottomVertex, self.nationName, self.capitolNum),
                 (-1, BuildType.centerEdge, self.nationName, self.capitolNum,
                  bclass),
                 (2, BuildType.bottomEdge, self.nationName, self.capitolNum,
                  bclass),
                 (1, BuildType.centerEdge, self.nationName, self.capitolNum,
                  bclass),
                 (1, BuildType.bottomEdge, self.nationName, self.capitolNum,
                  bclass)),
                ((-1, BuildType.topEdge),),
                requireLand=rland, requireWater=rwater)
        elif self.pos.d == BuildType.centerEdge:
            return shard.checkBuildableRequirements(self.block, self.pos,
                ((-1, BuildType.topVertex, self.nationName, self.capitolNum),
                 (-1, BuildType.bottomVertex, self.nationName, self.capitolNum),
                 (-1, BuildType.topEdge, self.nationName, self.capitolNum,
                  bclass),
                 (-1, BuildType.bottomEdge, self.nationName, self.capitolNum,
                  bclass),
                 (2, BuildType.bottomEdge, self.nationName, self.capitolNum,
                  bclass),
                 (4, BuildType.topEdge, self.nationName, self.capitolNum,
                  bclass)),
                ((-1, BuildType.centerEdge),),
                requireLand=rland, requireWater=rwater)
        elif self.pos.d == BuildType.bottomEdge:
            return shard.checkBuildableRequirements(self.block, self.pos,
                ((-1, BuildType.bottomVertex, self.nationName, self.capitolNum),
                 (5, BuildType.topVertex, self.nationName, self.capitolNum),
                 (-1, BuildType.centerEdge, self.nationName, self.capitolNum,
                  bclass),
                 (4, BuildType.topEdge, self.nationName, self.capitolNum,
                  bclass),
                 (5, BuildType.centerEdge, self.nationName, self.capitolNum,
                  bclass),
                 (5, BuildType.topEdge, self.nationName, self.capitolNum,
                  bclass)),
                ((-1, BuildType.bottomEdge),),
                requireLand=rland, requireWater=rwater)
        else:
            return False
            
    def _checkUpgradeSettlement(self, shard):
        """Check if this buildable can upgrade the current location."""
        return shard.checkBuildableRequirements(self.block, self.pos,
            ((-1, self.pos.d, self.nationName, self.capitolNum,
              Settlement),),
            ())

    def copy(self):
        return copy.copy(self)

    def getList(self):
        """Returns the buildable serialized in a list."""
        l = [self.pos.x, self.pos.y, self.pos.d, self.nationName,
             self.capitolNum, self.colors]
        return l

    def serialize(self):
        """Return a serialized copy of this buildable."""
        l = [BuildType.objects.index(self.__class__)]
        l.extend(self.getList())
        return pickle.dumps(l)

    def isInCapitol(self, nation, capitolNumber):
        """Returns True if this buildable is in the given nation's capitol."""
        return nation == self.nationName and capitolNumber == self.capitolNum

    def isMoveable(self):
        """Is this buildable moveable."""
        return False

    def canMove(self):
        """Can this buildable be moved right now."""
        return self.isMoveable()


class Settlement(Buildable):
    """A buildable settlement."""
    classId = 's'

    def getGather(self):
        return 1
               
    def getCost(self):
        return [-1, -1, -1, -1, 0, 0]

    def getVision(self):
        return 15

    def checkBuild(self, shard):
        return self._checkBuildVertex(shard)

    def isMoveable(self):
        return False


class Port(Buildable):
    """A buildable port."""
    classId = 'p'

    def getGather(self):
        return 0
               
    def getCost(self):
        return [-1, -1, 0, 0, -2, 0]

    def getVision(self):
        return 15

    def checkBuild(self, shard):
        return self._checkBuildVertex(shard, requireWater=True)

    def isMoveable(self):
        return False


class City(Buildable):
    """A buildable city."""
    classId = 'c'

    def getGather(self):
        return 2
               
    def getCost(self):
        return [0, 0, 0, -2, -3, 0]

    def getVision(self):
        return 18

    def checkBuild(self, shard):
        return self._checkUpgradeSettlement(shard)

    def isMoveable(self):
        return False


class Road(Buildable):
    """A buildable road."""
    classId = 'r'

    def getGather(self):
        return 0
               
    def getCost(self):
        return [-1, 0, -1, 0, 0, 0]

    def getVision(self):
        return 8

    def checkBuild(self, shard):
        return self._checkBuildEdge(shard, Road, True, False)

    def isMoveable(self):
        return False


class Sloop(Buildable):
    """A buildable sloop."""
    classId = 'f'

    def getGather(self):
        return 0

    def getCost(self):
        return [0, 0, 0, 0, 0, 0]

    def getVision(self):
        return 7

    def checkBuild(self, shard):
        return self._checkBuildShip(shard)

    def isMoveable(self):
        return True

    def canMove(self):
        return True


class BuildType:
    """Defines buildable types."""
    objects = [Settlement, City, Port, Road, Sloop]
    topEdge, centerEdge, bottomEdge, topVertex, bottomVertex, middle = range(6)
    dToJSON = ['t', 'c', 'b', 't', 'b', 'm']
    JSONtod = ['t', 'c', 'b', 'tv', 'bv', 'm']
