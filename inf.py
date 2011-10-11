import copy
import random
import math

from google.appengine.ext import db
from google.appengine.api import memcache


# Block size.
BLOCK_SIZE = 50
CAPITOL_SPACING = 6

def validBlockCoord(coord):
    return 0 <= coord.x < BLOCK_SIZE and 0 <= coord.y < BLOCK_SIZE


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

    def distanceTo(self, vect):
        x = self.x - vect.x
        y = self.y - vect.y
        return math.sqrt(x*x + y*y)

    def getBlockJSONId(self):
        return str(self.x) + '_' + str(self.y)

    def getList(self):
        return [self.x, self.y, self.d]

    def getListPos(self):
        return self.x + BLOCK_SIZE * self.y

    def isInBlockBounds(self):
        return 0 <= self.x < BLOCK_SIZE and 0 <= self.y < BLOCK_SIZE

    def getBlockVect(self):
        return Vect(self.x // BLOCK_SIZE, self.y // BLOCK_SIZE)

    def getRelativeVect(self):
        return Vect(self.x % BLOCK_SIZE, self.y % BLOCK_SIZE, self.d)


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
    none, water, field, pasture, forest, hills, mountain, desert,\
        goldmine, volcano, fish = range(11)


def isGoodStartType(tiletype):
    """Returns if a tile is good to start a capitol on."""
    return tiletype != TileType.water and tiletype != TileType.fish and\
           tiletype != TileType.volcano


def tileDirMove(coord, d):
    """Get the first tile coordinate in direction d from the given coord."""
    out = Vect(coord.x, coord.y)
    if d == 0:
        out.x += 1
        return out
    elif d == 3:
        out.x -= 1
        return out
    elif d == 1 or d == 2:
        out.y -= 1
    elif d == 4 or d == 5:
        out.y += 1
    if (coord.y % 2 == 0) and (d == 2 or d == 4):
        out.x -= 1
    elif coord.y % 2 and (d == 1 or d == 5):
        out.x += 1
    return out


class DatabaseObject:
    """A wrapper for a Database model.

    The getKeyName() and dbget() methods must be overloaded and modelClass must
    be defined as the associated db.Model class.
    """
    _model = None
    _useCached = False

    def load(self, use_cached=True):
        """Load or reload Block from cache/database."""
        # Memcache.
        self._useCached = use_cached
        if self._useCached:
            self._model = memcache.get(self.getKeyName())
        # Database.
        if not self._model:
            self.dbGet()
            self.cache()

    def save(self):
        """Store model state to database."""
        if (self.exists()):
            self.put()
            self.cache()

    def put(self):
        db.put(self._model)

    def cache(self, timeout=60):
        """Store Model state to cache."""
        if (self.exists()):
            memcache.set(self.getKeyName(), self._model, time=60*timeout)

    def atomic(self, method, *args, **kwargs):
        """Load the model and execute function in an atomic transaction.

        The updated object is cached and reloaded if the transaction failed.
        """
        if db.run_in_transaction(method, self, *args, **kwargs):
            self.cache()
            return True
        else:
            self.load()
            return False

    def exists(self):
        """Returns True if the Model has been successfully loaded."""
        return self._model is not None

    def setModel(self, model):
        self._model = model

    def dbGet(self, parent=None):
        """Get the model from the database."""
        self._model = self.modelClass.get_by_key_name(self.getKeyName(),
                                                      parent=parent)

    def loadOrCreate(self, parent=None, **kwags):
        """Gets the model from the database, creating it if it doesn't exist."""
        self._model = self.modelClass.get_or_insert(self.getKeyName(),
                                                    parent=parent, **kwags)
        self.cache()

    def getKeyName(self):
        """Returns the key_name for the model in the database."""
        raise NotImplementedError, "getKeyName() is not implemented."
