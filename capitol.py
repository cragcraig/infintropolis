from google.appengine.ext import db

import inf
import algorithms
import buildable
import worldshard


class CapitolModel(db.Model):
    """A database model representing a Capitol."""
    nation = db.StringProperty(required=True, indexed=False)
    number = db.IntegerProperty(required=True, indexed=False)
    location = db.ListProperty(int, indexed=False, required=True)
    hasSet = db.BooleanProperty(required=True, indexed=False)
    lumber = db.IntegerProperty(required=True, indexed=False)
    wool = db.IntegerProperty(required=True, indexed=False)
    brick = db.IntegerProperty(required=True, indexed=False)
    grain = db.IntegerProperty(required=True, indexed=False)
    ore = db.IntegerProperty(required=True, indexed=False)
    gold = db.IntegerProperty(required=True, indexed=False)


class Capitol(inf.DatabaseObject):
    """Represents a connected group of buildables with a single origin."""
    modelClass = CapitolModel

    def __init__(self, nation=None, number=None, model=None, load=True):
        """Load CapitolModel from cache/database.

        If create is set to True and the origin Vect is supplied the capitol
        will be added to the database.
        """
        inf.DatabaseObject.__init__(self)
        self._nation = nation
        if model:
            self.setModel(model)
            self._nationName = model.nation
            self._number = model.number
        else:
            self._nationName = nation.getName()
            self._number = number
        # Load or create CapitolModel.
        if not model and load and self._nation and self._number is not None and\
           self._number < self._nation.getCapitolCount():
            self.load()
            if not self.exists():
                self.create()
            self.updateLocationLogic()

    def create(self):
        """Creates a new Capitol model."""
        self.loadOrCreate(nation=self.getNationName(), number=self._number,
                          hasSet=False, location=[],
                          lumber=4, wool=4, brick=4, grain=2, ore=3, gold=6)

    def getNationName(self):
        """Returns the name of the controlling nation."""
        return self._nationName

    def getJSON(self):
        """Return JSON dictionary."""
        assert self._nation
        return {'nation': self.getNationName(),
                'name': self._nation.getCapitolName(self._number),
                'number': self._number,
                'capitol_count': self._nation.getCapitolCount(),
                'bx': self._model.location[0],
                'by': self._model.location[1],
                'x': self._model.location[2],
                'y': self._model.location[3],
                'resources': self.getResourceList()}

    def getResourceList(self):
        """Get Capitol's resources in list form."""
        return [self._model.lumber, self._model.wool, self._model.brick,
                self._model.grain, self._model.ore, self._model.gold]

    def hasLocation(self):
        """Returns true if a location has been assigned.

        This location is not required to be permanent unless hasSet is True.
        """
        return len(self._model.location) > 0

    def hasSetLocation(self):
        """Return whether this capitol location is permanent."""
        return self._model.hasSet

    def getLocationBlockVect(self):
        """Return the block where this Capitol originates."""
        return inf.Vect(self._model.location[0], self._model.location[1])

    def getLocationVect(self):
        """Return the position where this Capitol originates."""
        return inf.Vect(self._model.location[2], self._model.location[3],
                    self._model.location[4])

    def updateLocationLogic(self):
        """Logic to update capitol origin location."""
        if self.hasSetLocation():
            return
        elif not self.hasLocation():
            blockVect, pos = algorithms.findOpenStart()
            if blockVect and pos:
                self.atomicSetLocation(blockVect, pos)
        if self.hasLocation():
            shard = worldshard.WorldShard()
            v = inf.WorldVect(self.getLocationBlockVect(),
                              self.getLocationVect())
            if not shard.hasBuildableAt(v.block, v.pos, v.pos.d,
                                        nation=self.getNationName(),
                                        capitol=self._number):
                build = buildable.NewSettlement(v.block, v.pos)
                build.build(shard, self._nation, self)
            if not self.hasSetLocation() and\
               shard.hasBuildableAt(v.block, v.pos, v.pos.d,
                                    nation=self.getNationName(),
                                    capitol=self._number):
                self.atomicSetHasLocation()

    def atomicSetLocation(self, blockVect, pos):
        """Atomic set location (not necessarily permanent)."""
        if db.run_in_transaction(Capitol._setLoc, self, blockVect, pos):
            self.cache()
        else:
            self.load()

    def _setLoc(self, blockVect, pos):
        self.dbGet()
        self._model.location = [blockVect.x, blockVect.y, pos.x, pos.y, pos.d]
        self.put()
        return True

    def atomicSetHasLocation(self):
        """Atomic set location (not permanent)."""
        if db.run_in_transaction(Capitol._setHasLocation, self):
            self.cache()
        else:
            self.load()

    def _setHasLocation(self):
        self.dbGet()
        self._model.hasSet = True
        self.put()
        return True

    def gatherResources(self, shard, roll):
        """Perform a resource gather event for this capitol."""
        if not self.exists() or not self.hasSetLocation():
            return
        gathered = [0]*6
        visited = set()
        self.recurseBuildables(shard, buildable.Buildable.gather, roll,
                               gathered)
        self.atomicResourceAdd(gathered, async=True)

    def recurseBuildables(self, shard, funct, *args, **kargs):
        """Call function for each buildable owned by this Capitol.

        funct: f(buildable, shard, *args)
        """
        if not self.exists() or not self.hasSetLocation():
            return
        visited = set()
        self._recurseBuildablesBlock(shard, visited,
                                     self.getLocationBlockVect(), funct,
                                     *args, **kargs)

    def _recurseBuildablesBlock(self, shard, visited, block, funct,
                                *args, **kargs):
        """Call function for every non-ship buildable owned by this capitol.

        Intended to be called by recurseBuildables().
        """
        if block in visited:
            return
        visited.add(block)
        m = shard.getBlock(block, isCore=False)
        if not m or not m.exists():
            return
        # Perform function for this block.
        bleedset = set()
        for b in m.getBuildablesList():
            if b.isInCapitol(self.getNationName(), self.getNumber())\
               and not b.isMoveable():
                funct(b, shard, *args)
                b.block.updateBleedSet(bleedset)
        # Recursively call occupied surrounding blocks.
        for v in bleedset:
            self._recurseBuildablesBlock(shard, visited, v, funct,
                                         *args, **kargs)

    def atomicResourceAdd(self, resources, async=False):
        """Atomically add a resource list to this capitol's resources."""
        if not any(resources):
            return True
        if db.run_in_transaction(Capitol.addResources, self, resources,
                                 async=async):
            self.cache()
            return True
        else:
            self.load()
            return False

    def addResources(self, resources, async=False, put=True):
        """Add a resource list to this capitol's resources.

        Intended to be run as an atomic transaction.
        """
        self.dbGet()
        if not any(resources):
            return True
        res = self.getResourceList()
        final = [res[i] + resources[i] for i in xrange(len(res))]
        if any(map(lambda x: x < 0, final)):
            return False
        self._model.lumber = final[inf.TileType.lumber]
        self._model.wool = final[inf.TileType.wool]
        self._model.brick = final[inf.TileType.brick]
        self._model.grain = final[inf.TileType.grain]
        self._model.ore = final[inf.TileType.ore]
        self._model.gold = final[inf.TileType.gold]
        if put:
            if async:
                self.put_async()
            else:
                self.put()
        return True

    def getNumber(self):
        return self._number

    def getKeyName(self):
        return self.getNationName() + ':' + str(self.getNumber())
