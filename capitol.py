from google.appengine.ext import db

import inf
from buildable import Buildable, BuildType


BUILDABLE_LIST_SIZE = 6


class CapitolModel(db.Model):
    """A database model representing a Capitol."""
    nation = db.StringProperty(required=True)
    number = db.IntegerProperty(required=True)
    location = db.ListProperty(int, indexed=False, required=True)
    unset = db.BooleanProperty(required=True, indexed=False)
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

    def create(self):
        """Creates a new Capitol model."""
        self.loadOrCreate(nation=self.getNationName(), number=self._number,
                          unset=True, location=[],
                          lumber=0, wool=0, brick=0, grain=0, ore=0, gold=0)

    def getNationName(self):
        """Returns the name of the controlling nation."""
        return self._nation.getName()

    def atomicSetLocation(self, blockVect, pos):
        """Atomic set location (not permanent)."""
        if db.run_in_transaction(Capitol._setLoc, self, blockVect, pos):
            self.cache()
        else:
            self.load()

    def _setLoc(self, blockVect, pos):
        self.dbGet()
        self._model.location = [blockVect.x, blockVect.y, pos.x, pos.y]
        self.put()

    def getNumber(self):
        return self._number

    def getKeyName(self):
        return self.getNationName() + ':' + str(self.getNumber())
