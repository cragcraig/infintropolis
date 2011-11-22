from google.appengine.ext import db

import inf
from inf import Vect
from buildable import Buildable, BuildType
from capitol import Capitol
from mapblock import MapBlock


class NationModel(db.Model):
    """A database model representing a Nation."""
    name = db.StringProperty(required=True, indexed=False)
    pwd = db.StringProperty(required=True, indexed=False)
    email = db.StringProperty(indexed=False)
    title = db.StringProperty(indexed=False)
    points = db.IntegerProperty(required=True, indexed=False)
    capitolcount = db.IntegerProperty(required=True, indexed=False)
    color1 = db.IntegerProperty(required=True, indexed=False)
    color2 = db.IntegerProperty(required=True, indexed=False)
    capitolnames = db.StringListProperty(required=True, indexed=False)


class Nation(inf.DatabaseObject):
    """Represents the set of all Capitols controlled by a single user."""
    modelClass = NationModel

    def __init__(self, name='', pwd='', email='', color1=0, color2=0,
                 create=False):
        """Load NationModel from cache/database.

        If create is set to True the nation will be added to the database.
        """
        inf.DatabaseObject.__init__(self)
        self._name = name
        self._pwd = pwd
        self._error = None
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
                          title='', points=0, capitolcount=1, color1=color1,
                          color2=color2, capitolnames=['Village #1'])
        # Confirm that this nation did not previously exist.
        self.checkPassword()

    def atomicSetCapitolName(self, number, name):
        """Set the name of a Capitol in a transaction."""
        if db.run_in_transaction(Nation._setCapitolName, self, number, name):
            self.cache()
        else:
            self.load()

    def atomicAddCapitol(self, name=None):
        """Increment the capitol count by 1 in a transaction."""
        if db.run_in_transaction(Nation._addCapitol, self, name):
            self.cache()
        else:
            self.load()

    def _addCapitol(self, name):
        self.dbGet()
        self._model.capitolcount += 1
        if name is None:
            name = 'Village #' + str(self._model.capitolcount)
        self._model.capitolnames.append(name)
        self.put()
        return True

    def _setCapitolName(self, number, name):
        self.dbGet()
        if number < self.getCapitolCount():
            self._model.capitolnames[number] = name
            self.put()
        return True

    def getCapitolCount(self):
        """Return the current number of capitols under this nation."""
        return int(self._model.capitolcount)

    def getCapitolName(self, number):
        """Get the name of capitol number."""
        return self._model.capitolnames[number]

    def getCapitolNamesList(self):
        """Get the list of capitol names."""
        return self._model.capitolnames

    def getJSON(self):
        """Get a JSON object for this nation data."""
        return {'name': self._name,
                'capitol_count': self.getCapitolCount(),
                'capitol_names': self.getCapitolNamesList()}

    def getColors(self):
        return [int(self._model.color1), int(self._model.color2)]

    def getName(self):
        return self._name

    def getKeyName(self):
        return 'nation:' + self._name
