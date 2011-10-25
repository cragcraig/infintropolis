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

    def __init__(self, pos, level, nationName=None, capitolNum=None):
        self.pos = pos.copy()
        self.level = int(level)
        self.nationName = nationName
        self.capitolNum = capitolNum

    def build(self, nation, capitol, buildableblock):
        """Adds this buildable in all necessary database models."""
        self.nationName = nation.getName()
        self.capitolNum = capitol.getNumber()
        self.block = buildableblock.getPos().copy()
        buildableblock.atomicBuild(self, nation.getColors())

    def checkBuild(self, worldshard):
        """Checks if this buildable can be built."""
        if self.level == BuildType.settlement:
            return self._checkBuildVertex(worldshard)
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

    def getSurroundingTiles(self):
        """Returns a list of the surrounding tile positions."""
        if self.pos.d == BuildType.topEdge:
            return [self.pos, inf.tileDirMove(self.pos, 2)]
        elif self.pos.d == BuildType.centerEdge:
            return [self.pos, inf.tileDirMove(self.pos, 3)]
        elif self.pos.d == BuildType.bottomEdge:
            return [self.pos, inf.tileDirMove(self.pos, 4)]
        elif self.pos.d == BuildType.topVertex:
            return [self.pos, inf.tileDirMove(self.pos, 2),
                    inf.tileDirMove(self.pos, 3)]
        elif self.pos.d == BuildType.bottomVertex:
            return [self.pos, inf.tileDirMove(self.pos, 4),
                    inf.tileDirMove(self.pos, 3)]
        else:
            return []


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
    return not jsont == 'r' and not jsont =='b'
