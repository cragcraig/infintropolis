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

    def __init__(self, pos):
        """Load BuildableModel from database.

        By default a BuildableModel will be generated and stored to the database
        if one does not exist.
        """
        self._pos = pos.copy() 
        self.load()

    def set(self, coord, tile):
        """Set the tile at a specified coordinate."""
        t = coord.x + inf.BLOCK_SIZE * coord.y
        self._model.tiletype[t] = tile.tiletype
        self._model.roll[t] = tile.roll

    def getId(self):
        """Construct a unique consistant identifier string for the Block."""
        return 'buildableblock_' + repr(int(self._pos.x)) + ',' +\
               repr(int(self._pos.y))

    def getGQL(self):
        return  "SELECT * FROM BuildableModel WHERE x = " + repr(self._pos.x) +\
                " AND y = " + repr(self._pos.y)
