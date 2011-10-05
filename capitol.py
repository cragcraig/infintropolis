from google.appengine.ext import db

import inf
from buildable import Buildable, BuildType


BUILDABLE_LIST_SIZE = 6


class CapitolModel(db.Model):
    """A database model representing a Capitol."""
    nation = db.StringProperty(required=True)
    number = db.IntegerProperty(required=True)
    lumber = db.IntegerProperty(required=True)
    wool = db.IntegerProperty(required=True)
    brick = db.IntegerProperty(required=True)
    grain = db.IntegerProperty(required=True)
    ore = db.IntegerProperty(required=True)
    gold = db.IntegerProperty(required=True)
    color1 = db.IntegerProperty(required=True)
    color2 = db.IntegerProperty(required=True)


class Capitol(inf.DatabaseObject):
    """Represents a connected group of buildables with a single origin."""
    modelClass = CapitolModel
    _nation = None
    _number = None

    def __init__(self, nation, number, origin=None, load=True):
        """Load CapitolModel from cache/database.

        If create is set to True and the origin Vect is supplied the capitol
        will be added to the database.
        """
        self._nation = nation
        self._number = number
        if load:
            self.load()

    def create(self, origin, color1, color2):
        """Creates a new Capitol model."""
        # TODO(craig): Should be an ancestor query to ensure consistancy.
        # TODO(craig): Atomic check&set to avoid race conditions.
        self.loadOrCreate(nation=self.getNationName(), number=self._number,
                          lumber=0, wool=0, brick=0, grain=0, ore=0, gold=0,
                          color1=color1, color2=color2)

    def getNationName(self):
        """Returns the name of the controlling nation."""
        return self._nation.getName()

    def getNumber(self):
        return self._number

    def getColors(self):
        return [int(self._model.color1), int(self._model.color2)]

    def getKeyName(self):
        return self.getNationName() + ':' + str(self.getNumber())
