from google.appengine.ext import db

import inf
import algorithms
from inf import Vect
from buildable import Buildable, BuildType
from mapblock import MapBlock

BUILDABLE_LIST_SIZE = 6


class CapitolModel(db.Model):
    """A database model representing a Capitol."""
    nation = db.StringProperty(required=True)
    number = db.IntegerProperty(required=True)
    location = db.ListProperty(int, indexed=False, required=True)
    hasSet = db.BooleanProperty(required=True, indexed=False)
    lumber = db.IntegerProperty(required=True)
    wool = db.IntegerProperty(required=True)
    brick = db.IntegerProperty(required=True)
    grain = db.IntegerProperty(required=True)
    ore = db.IntegerProperty(required=True)
    gold = db.IntegerProperty(required=True)


class Capitol(inf.DatabaseObject):
    """Represents a connected group of buildables with a single origin."""
    modelClass = CapitolModel
    _nation = None
    _number = None

    def __init__(self, nation, number, load=True):
        """Load CapitolModel from cache/database.

        If create is set to True and the origin Vect is supplied the capitol
        will be added to the database.
        """
        self._nation = nation
        self._number = number
        if load and self._number < self._nation.getCapitolCount():
            self.load()
            if not self.exists():
                self.create()
            self.updateLocationLogic()

    def create(self):
        """Creates a new Capitol model."""
        self.loadOrCreate(nation=self.getNationName(), number=self._number,
                          hasSet=False, location=[],
                          lumber=0, wool=0, brick=0, grain=0, ore=0, gold=0)

    def getNationName(self):
        """Returns the name of the controlling nation."""
        return self._nation.getName()

    def getJSON(self):
        """Return JSON dictionary."""
        return {'number': self._number,
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

        This location is not required to be permanent.
        """
        return len(self._model.location) > 0

    def hasSetLocation(self):
        """Return whether this capitol location is permanent."""
        return self._model.hasSet

    def updateLocationLogic(self):
        """Logic to update capitol origin location."""
        if self.hasSetLocation():
            return
        elif not self.hasLocation():
            blockVect, pos = algorithms.findOpenStart()
            if blockVect and pos:
                self.atomicSetLocation(blockVect, pos)
        if self.hasLocation(): #TODO(craig): and not settlementExists()
            #TODO(craig): Check that build can actually occur.
            block = MapBlock(Vect(self._model.location[0],
                                  self._model.location[1]))
            build = Buildable(Vect(self._model.location[2],
                                   self._model.location[3],
                                   self._model.location[4]),
                              BuildType.settlement)
            build.build(self._nation, self, block)
        if not self.hasSetLocation(): #TODO(craig) and settlementExists()
            self.atomicSetHasLocation()

    def atomicSetLocation(self, blockVect, pos):
        """Atomic set location (not permanent)."""
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

    def getNumber(self):
        return self._number

    def getKeyName(self):
        return self.getNationName() + ':' + str(self.getNumber())
