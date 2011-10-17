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
    """Enum for building types."""
    topEdge, centerEdge, bottomEdge, topVertex, bottomVertex = range(5)
    dToJSON = ['t', 'c', 'b', 't', 'b']

    settlement, city, road, ship = range(4)
    tToJSON = ['s', 'c', 'r', 'b']
    LOSVision = [15, 25, 8, 10]
