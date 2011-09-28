import random
import cgi

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
import simplejson as json

import request
from session import Session
from inf import Vect
from buildable import Buildable, BuildType
from mapblock import MapBlock
from nation import Nation
from capitol import Capitol

class GetBlock(request.Handler):
    """Handle MapBlock requests."""

    def get(self):
        """Return requested data."""
        self.response.headers['Content-Type'] = 'text/plain'

        # Check user.
        if not self.loadNation():
            return

        # Check coordinates.
        form = cgi.FieldStorage()
        if not self.inForm(form, 'x', 'y'):
            return

        # Retrieve MapBlock.
        block = MapBlock(Vect(form.getfirst('x'), form.getfirst('y')))
        r = {'mapblock': block.getString(),
             'buildableblock': block.getBuildableBlock().getJSONList()}
        j = json.JSONEncoder().encode(r)
        self.response.out.write(j)


class SetBlock(request.Handler):
    """Handle set requests."""

    def get(self):
        """Return requested data."""
        self.response.headers['Content-Type'] = 'text/plain'

        # Check user.
        if not self.loadNation():
            return

        # Check coordinates.
        form = cgi.FieldStorage()
        if not self.inForm(form, 'set'):
            return
        setType = form.getfirst('set')

        # Do Set.
        if setType == 'buildable':
            # TODO(craig): Build new buildable.
            return
        elif setType == 'capitol':
            # TODO(craig): Create new capitol.
            return

        # TODO(craig): Return updated map and buildable data.
        self.response.out.write(block.getString())


application = webapp.WSGIApplication(
                                     [('/', Session),
                                      ('/get/map.*', GetBlock),
                                      ('/session.*', Session)],
                                     debug=True)


def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
