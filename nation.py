from google.appengine.ext import db
from google.appengine.api import memcache


class NationModel(db.Model):
    """A database model representing a Nation (User)."""
    x = db.IntegerProperty(required=True)
    y = db.IntegerProperty(required=True)
    tiletype = db.ListProperty(int, indexed=False)
    roll = db.ListProperty(int, indexed=False)


class Nation:
    
