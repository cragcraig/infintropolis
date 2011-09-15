from google.appengine.ext import db

import inf
from inf import Buildable


class CapitolModel(db.Model):
    """A database model representing a Capitol."""
    nation = db.StringProperty(required=True)
    number = db.IntegerProperty(required=True)
    x = db.IntegerProperty(required=True)
    y = db.IntegerProperty(required=True)
    north = db.IntegerProperty(required=True)
    west = db.IntegerProperty(required=True)
    south = db.IntegerProperty(required=True)
    east = db.IntegerProperty(required=True)
    resources = db.ListProperty(int, indexed=False)
    buildables = db.ListProperty(int, indexed=False)


class Capitol(inf.DatabaseObject):
    """Represents a connected group of buildables with a single origin."""
    _pos = Buildable(0, 0, BuildType.top, BuildType.city)
    _nation = None
    _number = None

    def __init__(self, nation='', number='', create=False):
        """Load CapitolModel from cache/database.

        If create is set to True the capitol will be added to the database.
        """
        self._name = name
        self._pwd = pwd
        if create:
            self.create()
        else:
            self.load(use_cached=False)

    def create(self):
        # TODO(craig): Should be an ancestor query to ensure consistancy.
        # TODO(craig): Atomic check&set to avoid race conditions.
        query = db.GqlQuery(self.getGQL())
        result = list(query.fetch(limit=1))
        if not len(result):
            self._model = NationModel(name=self._name, pwd=self._pwd, email='',
                                      title='', points=0, capitols=[])
            self.save()

    def getId(self):
        return 'capitol_' + repr(int(self._pos.x)) + "_" + repr(int(self._pos.y))

    def getGQL(self):
        return "SELECT * FROM CapitolModel " +\
               "WHERE nation = '" + self._nation + "' " +\
               "AND number = " + repr(int(self._number))
