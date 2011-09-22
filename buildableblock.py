import random

from google.appengine.ext import db
from google.appengine.api import memcache

import inf
from inf import Vect, Tile, TileType


class BuildableModel(db.Model):
    """A database model representing a 50x50 block of tiles."""
    x = db.IntegerProperty(required=True)
    y = db.IntegerProperty(required=True)
    buildables = db.ListProperty(int, indexed=False)


class BuildableBlock(inf.DatabaseObject):
    """A block of map tiles."""
    _pos = Vect(0,0)

    def __init__(self, pos, create=False):
        """Load BuildableModel from database.

        By default a new BuildableModel will not be generated.
        """
        self._pos = pos.copy() 
        if create:
            self.create()
        else:
            self.load()

    def create(self):
        # TODO(craig): Should be an ancestor query to ensure consistancy.
        # TODO(craig): Atomic check&set to avoid race conditions.
        self._model = CapitolModel(x=self._pos.x, y=self._pos.y, buildables=[])
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
        """Construct a unique consistant identifier string for the Block."""
        return 'buildableblock_' + str(self._pos.x) + ',' + str(self._pos.y)

    def getGQL(self):
        return  "SELECT * FROM BuildableModel WHERE x = " + str(self._pos.x) +\
                " AND y = " + str(self._pos.y)
