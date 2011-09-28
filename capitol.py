from google.appengine.ext import db

import inf
from buildable import Buildable, BuildType


BUILDABLE_LIST_SIZE = 6


class CapitolModel(db.Model):
    """A database model representing a Capitol."""
    nation = db.StringProperty(required=True)
    number = db.IntegerProperty(required=True)
    north = db.IntegerProperty(required=True)
    west = db.IntegerProperty(required=True)
    south = db.IntegerProperty(required=True)
    east = db.IntegerProperty(required=True)
    lumber = db.IntegerProperty(required=True)
    wool = db.IntegerProperty(required=True)
    brick = db.IntegerProperty(required=True)
    grain = db.IntegerProperty(required=True)
    ore = db.IntegerProperty(required=True)
    gold = db.IntegerProperty(required=True)
    buildables = db.ListProperty(int, indexed=False)


class Capitol(inf.DatabaseObject):
    """Represents a connected group of buildables with a single origin."""
    _nation = None
    _number = None

    def __init__(self, nation, number, origin=None, create=False):
        """Load CapitolModel from cache/database.

        If create is set to True and the origin Vect is supplied the capitol
        will be added to the database.
        """
        self._nation = nation
        self._number = number
        assert not create or origin
        if create and origin:
            self.create(origin)
        elif not create:
            self.load()

    def create(self, origin):
        """Creates a new Capitol model.

        You are responsible for saving the model.
        """
        # TODO(craig): Should be an ancestor query to ensure consistancy.
        # TODO(craig): Atomic check&set to avoid race conditions.
        self._model = CapitolModel(nation=self._nation, number=self._number,
                                   north=origin.y, west=origin.x,
                                   south=origin.y, east=origin.x,
                                   lumber=0, wool=0, brick=0, grain=0, ore=0,
                                   gold=0, buildables=[])

    def addBuildable(self, buildable):
        self._model.buildables.extend(buildable.getList())
        self._model.buildables.extend([buildable.block.x, buildable.block.y])
        # Update capitol bounds.
        if buildable.block.x > self._model.east:
            self._model.east = buildable.block.x
        if buildable.block.x < self._model.west:
            self._model.west = buildable.block.x
        if buildable.block.y > self._model.south:
            self._model.south = buildable.block.y
        if buildable.block.y < self._model.north:
            self._model.north = buildable.block.y

    def delBuildable(self, pos):
        p = pos.getList()
        lp = len(p)
        for i in xrange(0, len(self._model.buildables), BUILDABLE_LIST_SIZE):
            if self._model.buildables[i:i+lp] == p:
                del self._model.buildables[i:i+BUILDABLE_LIST_SIZE]
                break

    def getNation(self):
        return self._name

    def getNumber(self):
        return self._number

    def getId(self):
        return 'capitol_' + self._nation + '_' + self._number

    def getGQL(self):
        return "SELECT * FROM CapitolModel " +\
               "WHERE nation = '" + self._nation + "' " +\
               "AND number = " + str(self._number)
