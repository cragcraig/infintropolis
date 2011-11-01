import random

import google.appengine.ext.db as db

import capitol
import inf
from inf import Vect, TileType
from mapblock import MapBlock


def findOpenStart():
    """Find or generate an unoccupied location to start a capitol."""
    startPos = None
    # Find space in an avaliable MapBlock.
    query = db.GqlQuery("SELECT * FROM BlockModel "
                        "WHERE isFullOfCapitols = FALSE "
                        "ORDER BY count DESC")
    for model in query:
        block = MapBlock(Vect(model.x, model.y), load=False)
        block.setModel(model)
        startPos = block.findOpenSpace()
        if startPos:
            return startPos

    # Pick empty start locations.
    x = 0
    query = db.GqlQuery("SELECT * FROM BlockModel "
                        "ORDER BY x DESC")
    r = query.fetch(1)
    if len(r):
        x = r[0].x + 1

    # Create new MapBlocks until space is found.
    while not startPos:
        block = MapBlock(Vect(x, random.randint(-10, 10)))
        startPos = block.findOpenSpace()
        x += 1
    return startPos


def performResourceGather(worldshard, roll, subroll):
    """Performs a resource gather event for the entire world.
    
    roll: An integer indicating which hexes will produce resources.
    subroll: An integer [0, 5] determining directional effects for volcanoes and
             fishing grounds.
    """
    query = capitol.CapitolModel.all()
    for model in query:
        if not model.hasSet:
            continue
        c = capitol.Capitol(model=model)
        c.gatherResources(worldshard, roll)
