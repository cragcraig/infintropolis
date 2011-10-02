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
    capitolcount = db.IntegerProperty(required=True, indexed=False)
    color1 = db.IntegerProperty(required=True, indexed=False)
    color2 = db.IntegerProperty(required=True, indexed=False)


class Nation(inf.DatabaseObject):
    """Represents the set of all Capitols controlled by a single user."""
    modelClass = NationModel
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
            self.checkPassword()

    def checkPassword(self):
        if self.exists() and self._pwd != self._model.pwd:
            self._model = None

    def create(self, email, color1, color2):
        """Creates a new nation.

        This includes creating an original capitol and settlement.
        """
        origin = Vect(0, 0)
        self.loadOrCreate(name=self._name, pwd=self._pwd, email=email,
                          title='', points=0, capitolcount=0, color1=color1,
                          color2=color2)
        # Confirm that this nation did not previously exist.
        self.checkPassword()
        if self.exists() and self.getCapitolCount() == 0:
            capitol = self.createNewCapitol(origin)
            #TODO(craig): Must be atomic.
            self.save()
            capitol.save()

    def createNewCapitol(self, originBlock):
        """Adds a new capitol.

        You are responsible for saving the updated nation and capitol models.
        """
        #TODO(craig): Must be atomic.
        c = Capitol(self, self._model.capitolcount, load=False)
        c.create(originBlock, self._model.color1, self._model.color2)
        self._model.capitolcount += 1
        return c

    def getCapitolCount(self):
        """Return the current number of capitols under this nation."""
        return int(self._model.capitolcount)

    def getName(self):
        return self._name

    def getKeyName(self):
        return 'nation:' + self._name
