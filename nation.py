from google.appengine.ext import db

import inf
from capitol import Capitol


class NationModel(db.Model):
    """A database model representing a Nation."""
    name = db.StringProperty(required=True)
    pwd = db.StringProperty(required=True)
    email = db.StringProperty(required=False)
    title = db.StringProperty(required=False)
    points = db.IntegerProperty(required=True)
    capitols = db.IntegerProperty(required=True)


class Nation(inf.DatabaseObject):
    """Represents the set of all Capitols controlled by a single user."""
    _error = None
    _name = None
    _pwd = None

    def __init__(self, name='', pwd='', create=False, email=''):
        """Load NationModel from cache/database.

        If create is set to True the nation will be added to the database.
        """
        self._name = name
        self._pwd = pwd
        if create:
            self.create(email)
        else:
            self.load()
            if self.exists() and self._pwd != self._model.pwd:
                self._model = None

    def create(self, email):
        # TODO(craig): Should be an ancestor query to ensure consistancy.
        # TODO(craig): Atomic check&set to avoid race conditions.
        query = db.GqlQuery(self.getGQL())
        result = list(query.fetch(limit=1))
        if not len(result):
            self._model = NationModel(name=self._name, pwd=self._pwd,
                                      email=email, title='', points=0,
                                      capitols=0)
            self.save()

    def createNewCapitol(self, origBuildable):
        c = Capitol(self._name, self._model.capitols, origBuildable,
                    create=True)
        self._model.capitols += 1
        return c

    def getCapitolCount(self):
        return int(self._model.capitols)

    def getId(self):
        return 'nation_' + self._name

    def getGQL(self):
        return "SELECT * FROM NationModel " +\
               "WHERE name = '" + self._name + "'"
