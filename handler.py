import random
import cgi

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import request
import inf
from session import Session
from inf import Vect
from buildable import Buildable, BuildType
from mapblock import MapBlock
from buildableblock import BuildableBlock
from nation import Nation
from capitol import Capitol


class GetBlock(request.Handler):
    """Handle MapBlock requests."""

    def get(self):
        """Return requested data."""
        # Check user.
        if not self.loadNation():
            return

        # Check coordinates.
        form = cgi.FieldStorage()
        if not self.inForm(form, 'bx', 'by'):
            return

        # Retrieve MapBlock.
        block = MapBlock(Vect(form.getfirst('bx'), form.getfirst('by')))
        r = {'mapblock': block.getString(),
             'buildableblock': block.getBuildableBlock().getJSONList()}
        self.writeJSON({block.getPos().getBlockJSONId(): r})


class GetBuildableBlock(request.Handler):
    """Handle BuildableBlock requests."""

    def get(self):
        """Return BuildableBlock data."""
        # Check user.
        if not self.loadNation():
            return

        # Check coordinates.
        form = cgi.FieldStorage()
        if not self.inForm(form, 'bx', 'by'):
            return

        # Retrieve MapBlock.
        block = BuildableBlock(Vect(form.getfirst('bx'), form.getfirst('by')))
        r = {'buildableblock': block.getJSONList()}
        self.writeJSON({block.getPos().getBlockJSONId(): r})


class Build(request.Handler):
    """Handle build requests."""

    def get(self):
        """Build building and return updated BuildableBlock."""
        # Check user.
        if not self.loadNation():
            return

        # Check arguments.
        form = cgi.FieldStorage()
        if not self.inForm(form, 'type', 'capitol', 'x', 'y', 'd',
                           'bx', 'by'):
            return

        # Construct parameters.
        pos = Vect(form.getfirst('x'), form.getfirst('y'),
                   BuildType.dToJSON.index(form.getfirst('d')))
        buildtype = BuildType.tToJSON.index(form.getfirst('type'))
        blockVect = Vect(form.getfirst('bx'), form.getfirst('by'))
        if not inf.validBlockCoord(pos):
            return
        # Load from database.
        nationName = self.getNation().getName()
        capitol = Capitol(self.getNation().getName(), form.getfirst('capitol'))
        buildableblock = BuildableBlock(blockVect)
        if not capitol or not buildableblock:
            return

        # Build.
        build = Buildable(pos, buildtype)
        build.build(capitol, buildableblock)
        capitol.save()
        buildableblock.save()

        # Return updated BuildableBlock.
        r = {'buildableblock': buildableblock.getJSONList()}
        self.writeJSON({buildableblock.getPos().getBlockJSONId(): r})


application = webapp.WSGIApplication(
                                     [('/', Session),
                                      ('/get/map.*', GetBlock),
                                      ('/get/build.*', GetBuildableBlock),
                                      ('/set/build.*', Build),
                                      ('/session.*', Session)],
                                     debug=True)


def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
