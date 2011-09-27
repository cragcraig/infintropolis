import copy
import random

from google.appengine.ext import db
from google.appengine.api import memcache


# Block size.
BLOCK_SIZE = 50


class Vect:
    """Vector containing an (x,y[,d]) coordinate."""
    x = None
    y = None
    d = None

    def __init__(self, x, y, d=0):
        self.x = int(x)
        self.y = int(y)
        self.d = int(d)

    def __eq__(self, other):
        return x == other.x and y == other.y and d == other.d

    def __ne__(self, other):
        return x != other.x or y != other.y or d != other.d

    def copy(self):
        return copy.copy(self)

    def getList(self):
        return [self.x, self.y, self.d]

    def getListPos(self):
        return self.x + BLOCK_SIZE * self.y

    def getBlockVect(self):
        return Vect(self.x // BLOCK_SIZE, self.y // BLOCK_SIZE)

    def getRelativeVect(self):
        return Vect(self.x % BLOCK_SIZE, self.y % BLOCK_SIZE, self.d)


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
    capitol = None

    def __init__(self, pos, level, capitol=None, block=None):
        self.pos = pos.copy()
        self.level = int(level)
        self.capitol = capitol
        if block:
            self.block = block.copy()

    def copy(self):
        return copy.copy(self)

    def getList(self):
        return self.getShortList().extend([self.capitol.getNation(),
                                           self.capitol.getNumber()])

    def getShortList(self):
        return self.pos.getList().append(self.level)


class BuildType:
    """Enum for building types."""
    topEdge, centerEdge, bottomEdge, topVertex, bottomVertex = range(5)
    dToJSON = ['t', 'c', 'b', 't', 'b']

    settlement, city, road, ship = range(4)


class Tile:
    """An individual resource tile."""
    tiletype = None
    roll = None

    def __init__(self, tiletype=None, roll=None):
        self.tiletype = tiletype
        self.roll = roll

    def copy(self):
        return copy.copy(self)

    def isWater(self):
        return self.tiletype is not None and self.tiletype == TileType.water

    def isLand(self):
        return (self.tiletype is not None and
                self.tiletype != TileType.water)

    def isDesert(self):
        return self.tiletype == TileType.desert

    def isRollable(self):
        return self.isLand() and not self.isDesert()

    def randomize(self):
        self._randResource()
        if self.isRollable():
            self._randRoll()
        else:
            self.roll = 0

    def _randRoll(self):
        self.roll = random.choice([2, 3, 3, 4, 4, 5, 5, 6, 6,
                                   8, 8, 9, 9, 10, 10, 11, 11, 12])

    def _randResource(self):
        t = random.randint(2, 7)
        if t == 7:
            t = random.randint(1, 20)
            if t == 1:
                t = 8
            elif t <= 4:
                t = 9
            elif t <= 12:
                t = 7
            else:
                t = random.randint(2, 6)
        self.tiletype = t


class TileType:
    """Enumeration for tile types."""
    none, water, field, pasture, forest, hills, mountain, desert, \
        goldmine, volcano, fish = range(11)


class DatabaseObject:
    """A wrapper for a Database model.

    The getId() and getGQL() methods must be overloaded.
    """
    _model = None
    _useCached = False

    def load(self, use_cached=False):
        """Load or reload Block from cache/database."""
        # Memcache.
        self._useCached = use_cached
        if self._useCached:
            self._model = memcache.get(self.getId())
        # Database.
        if not self._model:
            query = db.GqlQuery(self.getGQL())
            result = list(query.fetch(limit=1))
            # Exists in database.
            if len(result):
                self._model = result[0]
                if self._useCached:
                    self.cache()

    def save(self):
        """Store MapBlock state to database."""
        if (self.exists()):
            if self._useCached:
                self.cache()
            db.put(self._model)

    def cache(self, timeout=15):
        """Store Model state to cache."""
        if (self.exists()):
            memcache.set(self.getId(), self._model, time=60*timeout)

    def exists(self):
        """Returns True if the Model has been successfully loaded."""
        return self._model is not None

    def getId(self):
        """Returns a unique identifier string for the Model."""
        raise NotImplementedError, 'getId() is not implemented in this class.'

    def getGQL(self):
        """Constructs a database query to select the Model."""
        raise NotImplementedError, 'getGQL() is not implemented in this class.'
