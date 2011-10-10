import random
import cgi

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import request
import inf
import algorithms
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
            self.writeLogoutJSON()
            return

        # Setup.
        request = self.getJSONRequest()
        response = {}

        # Retrieve MapBlocks and BuildableBlocks.
        for reqblock in request:
            if self.inDict(reqblock, 'x', 'y'):
                block = MapBlock(Vect(reqblock['x'], reqblock['y']))
                response[block.getPos().getBlockJSONId()] = {
                    'mapblock': block.getString(),
                    'buildableblock': block.getBuildableBlock().getJSONList()}

        self.writeJSON(response)


class GetBuildableBlock(request.Handler):
    """Handle BuildableBlock requests."""

    def get(self):
        """Return BuildableBlock data."""
        # Check user.
        if not self.loadNation():
            self.writeLogoutJSON()
            return

        # Setup.
        request = self.getJSONRequest()
        response = {}

        # Retrieve BuildableBlocks.
        for reqblock in request:
            if self.inDict(reqblock, 'x', 'y'):
                block = BuildableBlock(Vect(reqblock['x'], reqblock['y']))
                response[block.getPos().getBlockJSONId()] = {
                    'buildableblock': block.getJSONList()}

        self.writeJSON(response)


class GetCapitol(request.Handler):
    """Handle Capitol requests."""

    def get(self):
        """Return requested data."""
        # Check user.
        if not self.loadNation():
            self.writeLogoutJSON()
            return

        # Setup.
        request = self.getJSONRequest()
        response = {}

        # Retrieve Capitol data.
        if self.inDict(reqblock, 'x', 'y'):
            block = MapBlock(Vect(reqblock['x'], reqblock['y']))
            response[block.getPos().getBlockJSONId()] = {
                'mapblock': block.getString(),
                'buildableblock': block.getBuildableBlock().getJSONList()}

        self.writeJSON(response)


class PostBuild(request.Handler):
    """Handle build requests."""

    def post(self):
        """Build building and return updated BuildableBlock."""
        # Check user.
        if not self.loadNation():
            self.writeLogoutJSON()
            return

        # Setup.
        request = self.getJSONRequest()
        response = {}
        # Check arguments.
        if not self.inDict(request, 'type', 'capitol', 'x', 'y', 'd', 'bx',
                           'by'):
            return

        # Construct parameters.
        pos = Vect(request['x'], request['y'],
                   BuildType.dToJSON.index(request['d']))
        buildtype = BuildType.tToJSON.index(request['type'])
        blockVect = Vect(request['bx'], request['by'])
        if not inf.validBlockCoord(pos):
            return
        # Load from database.
        nationName = self.getNation().getName()

        #TODO(craig): Don't use memcache.
        #TODO(craig): Update capitol in a transaction (atomic).
        capitol = Capitol(self.getNation(), request['capitol'])

        buildableblock = BuildableBlock(blockVect)
        if not capitol or not buildableblock:
            return

        # Build.
        build = Buildable(pos, buildtype)
        build.build(self.getNation(), capitol, buildableblock)

        # Return updated BuildableBlock.
        r = {'buildableblock': buildableblock.getJSONList()}
        self.writeJSON({buildableblock.getPos().getBlockJSONId(): r})


class GetDebug(request.Handler):
    """Handle Debug requests."""

    def get(self):
        """Return requested data."""
        # Check user.
        if not self.loadNation():
            self.writeLogoutJSON()
            return

        # Debug response.
        r = algorithms.findOpenStart()
        self.writeJSON(r)


application = webapp.WSGIApplication(
                                     [('/', Session),
                                      ('/get/debug.*', GetDebug),
                                      ('/get/capitol.*', GetCapitol),
                                      ('/get/map.*', GetBlock),
                                      ('/get/build.*', GetBuildableBlock),
                                      ('/set/build.*', PostBuild),
                                      ('/session.*', Session)],
                                     debug=True)


def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
