import google.appengine.ext.db as db

def findOpenStart():
    startPos = None

    # Find space in an avaliable MapBlock.
    query = db.GqlQuery("SELECT * FROM MapBlock WHERE isFullOfCapitols = FALSE")
    for mapblock in query:
        startPos = mapblock.findOpenSpace()
        if (startPos):
            return startPos

    # TODO(craig): Create new MapBlocks until space is found.
    return None
