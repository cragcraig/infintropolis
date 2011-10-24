import random

#import webapp2
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import request
import inf
import algorithms
from session import Session
from inf import Vect
from worldshard import WorldShard
from buildable import Buildable, BuildType
from mapblock import MapBlock
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
        shard = WorldShard()

        # Retrieve MapBlocks.
        for reqblock in request:
            if self.inDict(reqblock, 'x', 'y'):
                v = Vect(reqblock['x'], reqblock['y'])
                shard.addBlock(v);

        # WorldShard.
        shard.loadDependencies()
        shard.applyLOS(self.getNation().getName())
        response = shard.getJSONDict()

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
            if self.inDict(reqblock, 'x', 'y', 'token'):
                block = MapBlock(Vect(reqblock['x'], reqblock['y']),
                                 generate_nonexist=False)
                if block.checkToken(reqblock['token']):
                    response[block.getPos().getBlockJSONId()] = {
                        'buildableblock': block.getBuildablesJSON()}

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
        if self.inDict(request, 'capitol'):
            capitolNum = request['capitol']
            capitol = Capitol(self.getNation(), capitolNum)
            if not capitol.exists() or not capitol.hasSetLocation():
                return
            response['capitol'] = capitol.getJSON()

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
                           'by') or request['type'] not in BuildType.tToJSON:
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

        buildableblock = MapBlock(blockVect)
        if not capitol or not buildableblock:
            return

        # Build.
        build = Buildable(pos, buildtype)
        build.build(self.getNation(), capitol, buildableblock)

        # Return updated BuildableBlock.
        r = {'buildableblock': buildableblock.getBuildablesJSON()}
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
        request = self.getJSONRequest()
        mapblock = MapBlock(Vect(request['bx'], request['by']))
        if mapblock.exists():
            self.writeJSON({'build': str(mapblock._model.buildables),
                            'nations': str(mapblock._model.nations),
                            'json': mapblock.getBuildablesJSON()})
        else:
            self.writeJSON("No such mapblock: " + str(mapblock._pos.x) + "," + str(mapblock._pos.y))


app = webapp.WSGIApplication(
                             [('/', Session),
                              ('/get/debug.*', GetDebug),
                              ('/get/capitol.*', GetCapitol),
                              ('/get/map.*', GetBlock),
                              ('/get/build.*', GetBuildableBlock),
                              ('/set/build.*', PostBuild),
                              ('/session.*', Session)],
                             debug=True)


def main():
  run_wsgi_app(app)

if __name__ == "__main__":
  main()
