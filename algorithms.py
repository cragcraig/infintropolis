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
        if (startPos):
            return startPos

    # TODO(craig): Create new MapBlocks until space is found.
    return None
