import copy


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

    def __init__(self, pos, level, nationName, capitolNum, blockVect):
        self.pos = pos.copy()
        self.level = int(level)
        self.nationName = nationName
        self.capitolNum = capitolNum
        self.block = blockVect.copy()

    def build(self, capitol, buildableblock):
        """Adds this buildable in all necessary database models."""
        capitol.addBuildable(self)
        buildableblock.addBuildable(self)

    def copy(self):
        return copy.copy(self)

    def getList(self):
        """Returns the pos and level as a list."""
        l = self.pos.getList()
        l.append(self.level)
        return l


class BuildType:
    """Enum for building types."""
    topEdge, centerEdge, bottomEdge, topVertex, bottomVertex = range(5)
    dToJSON = ['t', 'c', 'b', 't', 'b']

    settlement, city, road, ship = range(4)
    tToJSON = ['s', 'c', 'r', 'b']
