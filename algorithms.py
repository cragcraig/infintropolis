import random

import google.appengine.ext.db as db

from inf import Vect
from mapblock import MapBlock
from buildableblock import BuildableBlock


def findOpenStart():
    startPos = None
    # Find space in an avaliable MapBlock.
    query = db.GqlQuery("SELECT * FROM BuildableModel "
                        "WHERE isFullOfCapitols = FALSE "
                        "ORDER BY count DESC")
    for buildmodel in query:
        buildableblock = BuildableBlock(Vect(buildmodel.x, buildmodel.y),
                                        load=False)
        buildableblock.setModel(buildmodel)
        mapblock = MapBlock(Vect(buildmodel.x, buildmodel.y),
                            buildable_block=buildableblock)
        startPos = mapblock.findOpenSpace()
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
        mapblock = MapBlock(Vect(x, random.randint(-10, 10)))
        startPos = mapblock.findOpenSpace()
        x += 1
    return startPos
