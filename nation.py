from google.appengine.ext import db

import inf


class NationModel(db.Model):
    """A database model representing a Nation."""
    name = db.StringProperty(required=True)
    pwd = db.StringProperty(required=True)
    email = db.StringProperty(required=False)
    title = db.StringProperty(required=False)
    points = db.IntegerProperty(required=True)
    capitols = db.ListProperty(int, indexed=False)


class Nation(inf.DatabaseObject):
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
        return 'nation_' + self._name

    def getGQL(self):
        return "SELECT * FROM NationModel " +\
               "WHERE name = " + self._name
