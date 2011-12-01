import re

#import webapp2
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import request
import inf
import algorithms
import buildable
from session import Session
from inf import Vect
from worldshard import WorldShard
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
        for reqblock in request['maps']:
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
        for reqblock in request['maps']:
            if self.inDict(reqblock, 'x', 'y', 'token'):
                block = MapBlock(Vect(reqblock['x'], reqblock['y']),
                                 generate_nonexist=False)
                if block.exists() and block.checkToken(reqblock['token']):
                    response[block.getPos().getBlockJSONId()] = {
                        'buildableblock': block.getBuildablesJSON()}

        capitol = Capitol(self.getNation(), self.getCapitolNum())
        if capitol.exists():
            response['capitol'] = capitol.getJSON()

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

        # Get current Capitol number, if none use 0.
        capitolNum = self.getCapitolNum()

        # Retrieve Capitol data.
        capitol = Capitol(self.getNation(), capitolNum)
        if not capitol.exists() or not capitol.hasSetLocation():
            return
        response['capitol'] = capitol.getJSON()
        response['nation'] = self.getNation().getJSON()

        if self.inDict(request, 'disableJump') and request['disableJump']:
            response['capitol']['disableJump'] = True

        self.setCookie('capitol', capitolNum)
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
        response = {'isBuildResult': True}
        # Check arguments.
        if not self.inDict(request, 'type', 'x', 'y', 'd', 'bx', 'by'):
            self.writeJSON(response)
            return

        # Construct parameters.
        pos = Vect(request['x'], request['y'])
        pos.setdFromJSON(request['d'])
        worldPos = inf.WorldVect(Vect(request['bx'], request['by']), pos)
        if not inf.validBlockCoord(pos):
            self.writeJSON(response)
            return

        # Load Capitol.
        nationName = self.getNation().getName()
        capitol = Capitol(self.getNation(), self.getCapitolNum())
        if not capitol.exists():
            self.writeJSON(response)
            return

        # Build.
        worldshard = WorldShard()
        build = buildable.new(request['type'], worldPos)
        build.build(worldshard, self.getNation(), capitol)

        # Return updated BuildableBlock.
        response = worldshard.getJSONBuildablesDict()
        response['isBuildResult'] = True
        response['capitol'] = capitol.getJSON()
        response['cn'] = capitol.getNumber()
        self.writeJSON(response)


class PostMove(request.Handler):
    """Handle move requests."""

    def post(self):
        """Perform move and return updated block data."""
        # Check user.
        if not self.loadNation():
            self.writeLogoutJSON()
            return

        # Setup.
        request = self.getJSONRequest()
        response = {'isMoveResult': True}

        # Check arguments.
        if not self.inDict(request, 'path'):
            self.writeJSON(response)
            return

        # Construct and check path.
        path = []
        i = 0
        for v in request['path']:
            path.append(inf.WorldVect(Vect(v['bx'], v['by']),
                                      Vect(v['x'], v['y'],
                                           buildable.BuildType.middle)))
            if not path[i].pos.isInBlockBounds():
                self.writeJSON(response)
                return

        # Do move.
        worldshard = WorldShard()
        worldshard.atomicPathBuildable(self.getNation(), path)
        
        # Update LOS.
        if self.inDict(request, 'maps'):
            for reqblock in request['maps']:
                if self.inDict(reqblock, 'x', 'y'):
                    v = Vect(reqblock['x'], reqblock['y'])
                    worldshard.addBlock(v);

        # Return updated block data.
        worldshard.loadDependencies()
        worldshard.applyLOS(self.getNation().getName())
        response.update(worldshard.getJSONDict())
        self.writeJSON(response)


class PostTrade(request.Handler):
    """Handle trade requests."""

    def post(self):
        """Perform trade and return updated Capitol data."""
        # Check user.
        if not self.loadNation():
            self.writeLogoutJSON()
            return

        # Setup.
        request = self.getJSONRequest()
        response = {'isTradeResult': True}

        # Check arguments.
        if not self.inDict(request, 'from', 'for')\
           or request['from'] == request['for'] or request['for'] == 'gold'\
           or request['from'] not in inf.TileType.resources\
           or request['for'] not in inf.TileType.resources:
            self.writeJSON(response)
            return

        # Construct parameters.
        tradeFrom = inf.TileType.resources.index(request['from'])
        tradeFor = inf.TileType.resources.index(request['for'])

        fromMult = -4
        if request['from'] == 'gold':
            fromMult = -1

        # Load Capitol.
        capitol = Capitol(self.getNation(), self.getCapitolNum())
        if not capitol.exists():
            self.writeJSON(response)
            return

        # Trade.
        trade = [0]*6
        trade[tradeFrom] = fromMult
        trade[tradeFor] = 1
        capitol.atomicResourceAdd(trade)

        # Return updated Capitol.
        response['capitol'] = capitol.getJSON()
        self.writeJSON(response)


class GetPostNation(request.Handler):
    """Handle nation requests."""

    def get(self):
        """Handle requests for Nation data."""
        # Check user.
        if not self.loadNation():
            self.writeLogoutJSON()
            return

        # Respond.
        response = {'nation': self.getNation().getJSON()}
        self.writeJSON(response)

    def post(self):
        """Handle Nation set requests."""
        # Check user.
        if not self.loadNation():
            self.writeLogoutJSON()
            return

        # Get parameters.
        request = self.getJSONRequest()
        response = {}
        new = False
        number = None
        if self.inDict(request, 'name'):
            name = request['name']
            if name == '':
                name = "New Village"
        else:
            return

        if self.inDict(request, 'new'):
            new = request['new']
        if self.inDict(request, 'number'):
            number = request['number']

        if not new and number is None:
            return

        # Check for valid name.
        if not re.match("[\w\d?!#%@&~ -]{3,32}$", name) or len(name) > 32:
            return

        # Create new Capitol.
        if new:
            self.getNation().atomicAddCapitol(name)
            response['isNewCapitol'] = True
        else:
            self.getNation().atomicSetCapitolName(number, name)

        # Respond.
        response.update({'nation': self.getNation().getJSON()})
        self.writeJSON(response)


class GetGather(request.Handler):
    """Handle gather events."""

    def get(self):
        """Perform a single world-wide gather event."""
        worldshard = WorldShard()
        roll = inf.generateDoubleRoll()
        subroll = inf.generateSingleRoll()
        if roll != 7:
            algorithms.performResourceGather(worldshard, roll, subroll)
        self.writeJSON({'roll': roll, 'subroll': subroll})


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
            self.writeJSON("No such mapblock: " + str(mapblock._pos.x) + ","
                           + str(mapblock._pos.y))


app = webapp.WSGIApplication(
                             [('/', Session),
                              ('/get/debug.*', GetDebug),
                              ('/get/capitol.*', GetCapitol),
                              ('/set/move.*', PostMove),
                              ('/get/map.*', GetBlock),
                              ('/get/build.*', GetBuildableBlock),
                              ('/set/build.*', PostBuild),
                              ('/set/trade.*', PostTrade),
                              ('/get/nation.*', GetPostNation),
                              ('/set/nation.*', GetPostNation),
                              ('/session.*', Session),
                              ('/gather.*', GetGather)],
                             debug=True)


def main():
  run_wsgi_app(app)

if __name__ == "__main__":
  main()
