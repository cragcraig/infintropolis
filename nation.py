from google.appengine.ext import db

import inf
from inf import Vect
from buildable import Buildable, BuildType
from capitol import Capitol
from mapblock import MapBlock


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
        """Creates a new nation.

        This includes creating an original capitol and settlement.
        """
        # TODO(craig): Should be an ancestor query to ensure consistancy.
        # TODO(craig): Atomic check&set to avoid race conditions.
        query = db.GqlQuery(self.getGQL())
        result = list(query.fetch(limit=1))
        if not len(result):
            origin = Vect(0, 0)
            self._model = NationModel(name=self._name, pwd=self._pwd,
                                      email=email, title='', points=0,
                                      capitols=0)
            capitol = self.createNewCapitol(origin)
            # create original settlement
            build = Buildable(Vect(5, 5), BuildType.settlement, self._name, 0,
                          origin)
            mapblock = MapBlock(origin)
            build.build(capitol, mapblock.getBuildableBlock())
            self.save()
            capitol.save()
            mapblock.getBuildableBlock().save()

    def createNewCapitol(self, originBlock):
        """Adds a new capitol.

        You are responsible for saving the updated nation and capitol models.
        """
        c = Capitol(self._name, self._model.capitols, originBlock,
                    create=True)
        self._model.capitols += 1
        return c

    def getCapitolCount(self):
        """Return the current number of capitols under this nation."""
        return int(self._model.capitols)

    def getId(self):
        return 'nation_' + self._name

    def getGQL(self):
        return "SELECT * FROM NationModel " +\
               "WHERE name = '" + self._name + "'"
