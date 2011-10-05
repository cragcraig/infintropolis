import random

from google.appengine.ext import db
from google.appengine.api import memcache

import inf
from buildable import BuildType
from inf import Vect, Tile, TileType


BUILDABLE_LIST_SIZE = 8


class BuildableModel(db.Model):
    """A database model representing a 50x50 block of tiles."""
    x = db.IntegerProperty(required=True)
    y = db.IntegerProperty(required=True)
    buildables = db.ListProperty(int, indexed=False)
    nations = db.StringListProperty(indexed=False)


class BuildableBlock(inf.DatabaseObject):
    """A block of buildables."""
    modelClass = BuildableModel
    _pos = Vect(0,0)

    def __init__(self, pos, use_cached=True):
        """Load BuildableModel from database.

        The model will be loaded from the database if it exists, otherwise an
        empty model will be created and stored to the database.
        """
        self._pos = pos.copy() 
        self.load(use_cached=use_cached)
        if not self.exists():
            self.loadOrCreate(x=self._pos.x, y=self._pos.y,
                              buildables=[], nations=[])

    def atomicBuild(self, buildable, colors):
        """Builds the buildable in an atomic database transaction."""
        if db.run_in_transaction(BuildableBlock._build, self, buildable,
                                 colors):
            self.cache()
        else:
            self.load()

    def _build(self, buildable, colors):
        """Builds the buildable. For use inside atomicBuild()."""
        self.dbGet()
        self._addBuildable(buildable, colors)
        self.put()
        return True

    def _addBuildable(self, buildable, colors):
        nationIndex = self._getNationIndex(buildable.nationName)
        assert len(colors) == 2
        self._model.buildables.extend(buildable.getList())
        self._model.buildables.extend(colors)
        self._model.buildables.extend([int(nationIndex), int(buildable.capitolNum)])

    def _delBuildable(self, pos):
        p = pos.getList()
        lp = len(p)
        for i in xrange(0, len(self._model.buildables), BUILDABLE_LIST_SIZE):
            if self._model.buildables[i:i+lp] == p:
                del self._model.buildables[i:i+BUILDABLE_LIST_SIZE]
                break

    def getPos(self):
        return self._pos

    def getJSONList(self):
        """Construct a list of dictionary representations of buildables."""
        return [{'x': int(self._model.buildables[i]),
                 'y': int(self._model.buildables[i+1]),
                 'd': BuildType.dToJSON[self._model.buildables[i+2]],
                 't': BuildType.tToJSON[self._model.buildables[i+3]],
                 'c1': self._int2hexcolor(self._model.buildables[i+4]),
                 'c2': self._int2hexcolor(self._model.buildables[i+5]),
                 'n': self._model.nations[self._model.buildables[i+6]],
                 'i': int(self._model.buildables[i+7])}
                for i in xrange(0, len(self._model.buildables),
                                BUILDABLE_LIST_SIZE)]

    def _getNationIndex(self, nationName):
        """Get the index of a nation in the model's nation list.

        Adds the nation if it does not exist. It is up to you to save the
        updated model to the database.
        """
        if nationName not in self._model.nations:
            self._model.nations.append(nationName)
        return self._model.nations.index(nationName)

    def _int2hexcolor(self, color):
        return "%06x" % color

    def getKeyName(self):
        return 'buildableblock:' + str(self._pos.x) + ',' + str(self._pos.y)
