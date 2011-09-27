import random

from google.appengine.ext import db
from google.appengine.api import memcache

import inf
from inf import Vect, Tile, TileType


BUILDABLE_LIST_SIZE = 6


class BuildableModel(db.Model):
    """A database model representing a 50x50 block of tiles."""
    x = db.IntegerProperty(required=True)
    y = db.IntegerProperty(required=True)
    buildables = db.ListProperty(int, indexed=False)


class BuildableBlock(inf.DatabaseObject):
    """A block of buildables."""
    _pos = Vect(0,0)

    def __init__(self, pos, create_new=False):
        """Load BuildableModel from database.

        By default a new BuildableModel will NOT be generated and the model
        will be loaded from the database. If create_new is True the database
        will not be checked before creating a new BuildableModel; it is up to
        you to prevent the creation of duplicate database entries.
        """
        self._pos = pos.copy() 
        if create_new:
            self.create()
        else:
            self.load()

    def create(self):
        # TODO(craig): Should be an ancestor query to ensure consistancy.
        # TODO(craig): Atomic check&set to avoid race conditions.
        self._model = BuildableModel(x=self._pos.x, y=self._pos.y,
                                     buildables=[])
        self.save()

    def addBuildable(self, buildable):
        self._model.buildables.extend(buildable.getList())

    def delBuildable(self, pos):
        p = pos.getList()
        for i in xrange(0, len(self._model.buildables), BUILDABLE_LIST_SIZE):
            if self._model.buildables[i:i+3] == p:
                del self._model.buildables[i:i+BUILDABLE_LIST_SIZE]
                break

    def getBuildablesJSON(self):
        """Construct a list of JSON string BuildableBlock representations."""
        return ['{x:' + str(int(self._model.buildables[i])) +\
                ',y:' + str(int(self._model.buildables[i+1])) +\
                ',d:' + inf.BuildType.dToJSON[self._model.buildables[i+1]] +\
                for i in xrange(0, len(self._model.buildables,
                                BUILDABLE_LIST_SIZE)]

    def getId(self):
        """Construct a unique consistant identifier string for the Block."""
        return 'buildableblock_' + str(self._pos.x) + ',' + str(self._pos.y)

    def getGQL(self):
        return  "SELECT * FROM BuildableModel WHERE x = " + str(self._pos.x) +\
                " AND y = " + str(self._pos.y)
