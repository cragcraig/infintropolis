from google.appengine.ext import db
from google.appengine.api import memcache

import infbase

class NationModel(db.Model):
    """A database model representing a Nation (User)."""
    name = db.StringProperty(required=True)
    pwd = db.StringProperty(required=True)
    email = db.StringProperty(required=False)
    points = db.IntegerProperty(required=True)
    capitols = db.ListProperty(int, indexed=False)


class Nation(infbase.DatabaseObject):
    _error = None
    _name = None
    _pwd = None

    def __init__(self, name='', pwd='', load=True):
        """Load NationModel from cache/database.

        If load is True (default) the nation will be loaded from the database.
        """
        self._name = name
        self._pwd = pwd
        if load:
            self.load(use_cached=False)

    def getId(self):
        return 'nation_' + self._name

    def getGQL(self):
        return "SELECT * FROM NationModel "
               "WHERE name = " + self._name + " AND "
               "pwd = " + self._pwd
