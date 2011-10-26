import copy

import inf


class Buildable:
    """Represents an buildable game object.

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
    pos = None
    level = None
    block = None
    nationName = None
    capitolNum = None
    validate = False

    def __init__(self, blockPos, pos, level, nationName=None, capitolNum=None,
                 validate=True):
        self.pos = pos.copy()
        self.block = blockPos.copy()
        self.level = int(level)
        self.nationName = nationName
        self.capitolNum = capitolNum
        self.validate = validate

    def build(self, worldshard, nation, capitol):
        """Adds this buildable in all necessary database models."""
        self.nationName = nation.getName()
        self.capitolNum = capitol.getNumber()
        block = worldshard.getBlock(self.block)
        if block:
            block.atomicBuild(self, nation.getColors())

    def checkBuild(self, worldshard):
        """Checks if this buildable can be built."""
        if not self.validate:
            return True
        # Perform type-specific validation.
        if self.level == BuildType.settlement:
            return self._checkBuildVertex(worldshard)
        else:
            return True
        if True:
            pass
        elif self.level == BuildType.road:
            return self._checkBuildRoad(worldshard)
        elif self.level == BuildType.ship:
            return self._checkBuildShip(worldshard)
        else:
            return self._checkBuildVertexUpgrade(worldshard)

    def _checkBuildVertex(self, worldshard):
        """Check if this buildable can be build at a vertex."""
        if self.pos.d == BuildType.topVertex:
            return worldshard.checkBuildableRequirements(self.block, self.pos,
                ((-1, BuildType.centerEdge, self.nationName),
                 (-1, BuildType.topEdge, self.nationName),
                 (2, BuildType.bottomEdge, self.nationName)),
                ((-1, BuildType.topVertex),
                 (-1, BuildType.bottomVertex),
                 (1, BuildType.bottomVertex),
                 (2, BuildType.bottomVertex)),
                 requireLand=True)
        elif self.pos.d == BuildType.bottomVertex:
            return worldshard.checkBuildableRequirements(self.block, self.pos,
                ((-1, BuildType.centerEdge, self.nationName),
                 (-1, BuildType.bottomEdge, self.nationName),
                 (4, BuildType.topEdge, self.nationName)),
                ((-1, BuildType.topVertex),
                 (-1, BuildType.bottomVertex),
                 (4, BuildType.topVertex),
                 (5, BuildType.topVertex)),
                 requireLand=True)
        else:
            return False

    def copy(self):
        return copy.copy(self)

    def getList(self):
        """Returns the pos and level as a list."""
        l = self.pos.getList()
        l.append(self.level)
        return l


class BuildType:
    """Enum for buildable types."""
    topEdge, centerEdge, bottomEdge, topVertex, bottomVertex = range(5)
    dToJSON = ['t', 'c', 'b', 't', 'b']
    JSONtod = ['t', 'c', 'b', 'tv', 'bv']

    settlement, city, road, ship = range(4)
    empty = -1
    tToJSON = ['s', 'c', 'r', 'b']
    LOSVision = [15, 18, 8, 8]


def JSONtod(jsont, jsond):
    """Get the correct d value from a json d value."""
    v = jsond
    if isJSONVertex(jsont):
        v += 'v'
    return BuildType.JSONtod.index(v)


def isJSONVertex(jsont):
    return jsont != 'r' and jsont != 'b'
