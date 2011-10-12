import random

import google.appengine.ext.db as db

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
        x = r[0].x

    # Create new MapBlocks until space is found.
    while not startPos:
        block = MapBlock(Vect(x, random.randint(-10, 10)))
        startPos = block.findOpenSpace()
        x += 1
    return startPos


def recurseLOS(pos, los, costmap, tiles, count):
    """Recursively performs line of sight calculations.

    pos: Current pos as a Vert().
    los: List containing LOS data for the MapBlock.
    costmap: List containing temporary LOS cost data for the MapBlock.
    tiles: List containing map tile data for the MapBlock.
    count: Current LOS counter.
    """
    index = pos.getListPos()
    if index < 0 or index > inf.BLOCK_SIZE * inf.BLOCK_SIZE:
        #TODO(craig): Can't do this, need to handle multi-map visibility.
        return
    if costmap[index] >= count:
        return
    los[index] = 1
    costmap[index] = count
    newcount = count - TileType.LOSCost[tiles[index]]
    if newcount <= 0:
        return
    for p in inf.listSurroundingTilePos(pos):
        recurseLOS(Vect(p[0], p[1]), los, costmap, tiles, newcount)
