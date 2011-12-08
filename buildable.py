import copy
import pickle
import time

import inf


# Object generators.

def unserialize(str, block):
    """Recreate a serialized buildable."""
    b = pickle.loads(str)
    o = new(b[0], inf.WorldVect(block, inf.Vect(b[1], b[2], b[3])))
    o.unserialize(*b[4:])
    return o


def new(classId, *args, **kwargs):
    """Create a buildable object of the specified classId type."""
    obj = _objects_dict[classId]
    return obj(*args, **kwargs)


# Base class.

class Buildable:
    """Base class for all buildable game objects. Should not be used directly.

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

    def __init__(self, worldPos):
        self.pos = worldPos.pos.copy()
        self.block = worldPos.block.copy()
        self.nationName = None
        self.capitolNum = None
        self.colors = (0, 0)
        self.jsonId = None

    def build(self, shard, nation, capitol):
        """Adds this buildable in all necessary database models."""
        self.nationName = nation.getName()
        self.capitolNum = capitol.getNumber()
        self.colors = nation.getColors()
        block = shard.getBlock(self.block)
        if block and self.checkBuild(shard):
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
        return self._attrGather
               
    def getCost(self):
        """Returns the cost of this buildable as a list."""
        return self._attrCost

    def getVision(self):
        return self._attrVision

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

    def _checkBuildNewVertex(self, shard, requireWater=False):
        if not self.pos.isVertex():
            return False
        """Check if this buildable can be built at a vertex."""
        if self.pos.d == BuildType.topVertex:
            return shard.checkBuildableRequirements(self.block, self.pos,
                (),
                ((-1, BuildType.topVertex),
                 (-1, BuildType.bottomVertex),
                 (1, BuildType.bottomVertex),
                 (2, BuildType.bottomVertex)),
                 requireLand=True, requireWater=requireWater)
        elif self.pos.d == BuildType.bottomVertex:
            return shard.checkBuildableRequirements(self.block, self.pos,
                (),
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
             self.capitolNum, self.colors, self.jsonId]
        return l

    def serialize(self):
        """Return a serialized copy of this buildable."""
        l = [self.classId]
        l.extend(self.getList())
        l.extend(self.getExtra())
        return pickle.dumps(l)

    def unserialize(self, nationName, capitolNumber, colors, jsonId, *args):
        """Unserialize basic attributes and send extras on."""
        self.nationName = nationName
        self.capitolNum = capitolNumber
        self.colors = colors
        self.jsonId = jsonId
        self.setExtra(*args)

    def setExtra(self):
        """Overload to implement object specific unserialization."""
        pass

    def getExtra(self):
        """Return an iterable of object specific attributes to serialize."""
        return ()

    def getExtraJSON(self):
        """Return object specific JSON attributes as a dict."""
        return ()

    def isInCapitol(self, nation, capitolNumber):
        """Returns True if this buildable is in the given nation's capitol."""
        return nation == self.nationName and capitolNumber == self.capitolNum

    def isMoveable(self):
        """Is this buildable moveable."""
        return self._attrMoveable

    def getJSONDict(self):
        """Get a JSON dict representation of this buildable."""
        json = {'x': self.pos.x,
                'y': self.pos.y,
                'd': self.pos.getJSONd(),
                't': self.classId,
                'c1': "%06x" % self.colors[0],
                'c2': "%06x" % self.colors[1],
                'n': self.nationName,
                'i': self.capitolNum,
                'id': self.jsonId}
        json.update(self.getExtraJSON())
        return json


# Game Objects.

class Settlement(Buildable):
    """A buildable settlement."""
    classId = 's'
    _attrGather = 1
    _attrMoveable = False
    _attrCost = [-1, -1, -1, -1, 0, 0]
    _attrVision = 15

    def checkBuild(self, shard):
        return self._checkBuildVertex(shard)


class NewSettlement(Settlement):
    """A settlement that does not require surrounding buildings or cost.
    
    This buildable will serialize as a normal settlement.
    """
    _attrCost = [0, 0, 0, 0, 0, 0]

    def checkBuild(self, shard):
        return self._checkBuildNewVertex(shard)


class Port(Buildable):
    """A buildable port."""
    classId = 'p'
    _attrGather = 0
    _attrMoveable = False
    _attrCost = [-1, -1, 0, 0, -2, 0]
    _attrVision = 15

    def checkBuild(self, shard):
        return self._checkBuildVertex(shard, requireWater=True)


class City(Buildable):
    """A buildable city."""
    classId = 'c'
    _attrGather = 2
    _attrMoveable = False
    _attrCost = [0, 0, 0, -2, -3, 0]
    _attrVision = 18

    def checkBuild(self, shard):
        return self._checkUpgradeSettlement(shard)


class Road(Buildable):
    """A buildable road."""
    classId = 'r'
    _attrGather = 0
    _attrMoveable = False
    _attrCost = [-1, 0, -1, 0, 0, 0]
    _attrVision = 8

    def checkBuild(self, shard):
        return self._checkBuildEdge(shard, Road, True, False)


# Ships.

class Ship(Buildable):
    """A generic ship."""
    _attrGather = 0
    _attrMoveable = True

    def __init__(self, *args):
        Buildable.__init__(self, *args)
        self.lastAction = 0
        self.health = self._attrHealth
        self.cargo = None

    def setExtra(self, lastAction, health, cargo=None):
        #TODO(craig): get rid of the None default for cargo here.
        self.lastAction = lastAction
        self.health = health
        self.cargo = cargo
 
    def getExtra(self):
        return (self.lastAction, self.health, self.cargo)

    def getExtraJSON(self):
        return {'act': self.getFreeActions(),
                'hp': self.health,
                'mhp': self._attrHealth,
                'res': self.getCargoList()}

    def checkBuild(self, shard):
        return self._checkBuildShip(shard)

    def getFreeActions(self):
        """Return the number of action points avaliable."""
        if self._attrRecover <= 0:
            return self._attrMaxActions
        return min(int((time.time() - self.lastAction)/self._attrRecover),
                   self._attrMaxActions)

    def subtractFreeActions(self, n):
        """Attempts to remove n action points.
        
        Returns True on success, False if n > current actions.
        """
        actions = self.getFreeActions()
        if n > actions:
            return False
        else:
            self.lastAction = time.time() - self._attrRecover * (actions - n)
            return True

    def clearFreeActions(self):
        """Remove all action points."""
        self.lastAction = time.time()

    def getDamage(self):
        """Get the current damage dealt by this ship."""
        return min(int(2 * self.health * self._attrDamage / self._attrHealth),
                   self._attrDamage)

    def hurt(self, dmg):
        """Damages the ship."""
        self.health -= dmg
        if self.health < 0:
            self.health = 0

    def isDead(self):
        """Return True if the ship's health is 0."""
        return self.health == 0

    def getCargoList(self):
        """Return the list of resources carried by this ship."""
        if self.cargo is None:
            return [0, 0, 0, 0, 0, 0]
        else:
            return self.cargo


class Sloop(Ship):
    """A buildable sloop."""
    classId = 'f'
    _attrCost = [0, 0, 0, 0, 0, 0]
    _attrVision = 7
    _attrMaxActions = 5
    _attrRecover = 0
    _attrDamage = 6
    _attrHealth = 10


class BuildType:
    """Defines buildable object position."""
    topEdge, centerEdge, bottomEdge, topVertex, bottomVertex, middle = range(6)
    dToJSON = ['t', 'c', 'b', 't', 'b', 'm']
    JSONtod = ['t', 'c', 'b', 'tv', 'bv', 'm']


# List of buildable objects.
_objects = frozenset([Settlement, City, Port, Road, Sloop])
_objects_dict = dict((o.classId, o) for o in _objects)
