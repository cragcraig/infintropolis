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
    email = db.StringProperty(indexed=False)
    title = db.StringProperty(indexed=False)
    points = db.IntegerProperty(required=True, indexed=False)
    capitols = db.IntegerProperty(required=True, indexed=False)
    color1 = db.IntegerProperty(required=True, indexed=False)
    color2 = db.IntegerProperty(required=True, indexed=False)


class Nation(inf.DatabaseObject):
    """Represents the set of all Capitols controlled by a single user."""
    _error = None
    _name = None
    _pwd = None

    def __init__(self, name='', pwd='', email='', color1=0, color2=0,
                 create=False):
        """Load NationModel from cache/database.

        If create is set to True the nation will be added to the database.
        """
        self._name = name
        self._pwd = pwd
        if create:
            self.create(email, color1, color2)
        else:
            self.load()
            if self.exists() and self._pwd != self._model.pwd:
                self._model = None

    def create(self, email, color1, color2):
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
                                      capitols=0, color1=color1, color2=color2)
            capitol = self.createNewCapitol(origin)
            # create original settlement
            build = Buildable(Vect(25, 25), BuildType.settlement)
            mapblock = MapBlock(origin)
            build.build(capitol, mapblock.getBuildableBlock())
            self.save()
            capitol.save()
            mapblock.getBuildableBlock().save()

    def createNewCapitol(self, originBlock):
        """Adds a new capitol.

        You are responsible for saving the updated nation and capitol models.
        """
        c = Capitol(self._name, self._model.capitols, load=False)
        c.create(originBlock, self._model.color1, self._model.color2)
        self._model.capitols += 1
        return c

    def getCapitolCount(self):
        """Return the current number of capitols under this nation."""
        return int(self._model.capitols)

    def getName(self):
        return self._name

    def getId(self):
        return 'nation_' + self._name

    def getGQL(self):
        return "SELECT * FROM NationModel " +\
               "WHERE name = '" + self._name + "'"
