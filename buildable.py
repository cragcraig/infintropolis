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

    def __init__(self, pos, level):
        self.pos = pos.copy()
        self.level = int(level)

    def build(self, capitol, buildableblock):
        """Adds this buildable in all necessary database models."""
        self.nationName = capitol.getNationName()
        self.capitolNum = capitol.getNumber()
        self.block = buildableblock.getPos().copy()
        buildableblock.addBuildable(self, capitol.getColors())

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
