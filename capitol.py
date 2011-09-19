from google.appengine.ext import db

import inf
from inf import Buildable


class CapitolModel(db.Model):
    """A database model representing a Capitol."""
    nation = db.StringProperty(required=True)
    number = db.IntegerProperty(required=True)
    north = db.IntegerProperty(required=True)
    west = db.IntegerProperty(required=True)
    south = db.IntegerProperty(required=True)
    east = db.IntegerProperty(required=True)
    resources = db.ListProperty(int, indexed=False)
    buildables = db.ListProperty(int, indexed=False)


class Capitol(inf.DatabaseObject):
    """Represents a connected group of buildables with a single origin."""
    _nation = None
    _number = None

    def __init__(self, nation='', number='', origBuildable=None, create=False):
        """Load CapitolModel from cache/database.

        If create is set to True and origBuildable is supplied the capitol will
        be added to the database.
        """
        self._name = nation
        self._number = number
        if create and origBuildable:
            self.create(origBuildable)
        elif not create:
            self.load()

    def create(self, origBuildable):
        # TODO(craig): Should be an ancestor query to ensure consistancy.
        # TODO(craig): Atomic check&set to avoid race conditions.
        pos = origBuildable.getBlockVect() 
        self._model = CapitolModel(nation=self._nation, number=self._number,
                                   north=pos.y, west=pos.x, south=pos.y,
                                   east=pos.x, resources=[0,0,0,0,0],
                                   buildables=[])
        self.addBuildable(origBuildable)
        self.save()

    def addBuildable(self, buildable):
        self._model.buildables.extend(buildable.getList())

    def delBuildable(self, pos):
        p = pos.getList()
        for i in xrange(0, len(self._model.buildables), 4):
            if self._model.buildables[i:i+3] == p:
                del self._model.buildables[i:i+4]
                break

    def getId(self):
        return 'capitol_' + repr(int(self._pos.x)) + "_" + repr(int(self._pos.y))

    def getGQL(self):
        return "SELECT * FROM CapitolModel " +\
               "WHERE nation = '" + self._nation + "' " +\
               "AND number = " + repr(int(self._number))
