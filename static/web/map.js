// settings
var scrollDelay = 100;
var dragDelay = 70;

// system globals
var canvas;
var ctx;
var mouseActive = true;
var mouseX;
var mouseY;
var pureMouseX;
var pureMouseY;
var clickMouseX;
var clickMouseY;
var movedMouse = false;
var initd = false;

var scrollId = null;
var scrollWE = 0;
var scrollNS = 0;

// globals
var screenX = 0;
var screenY = 0;
var screenOffsetX = 0;
var screenOffsetY = 0;
var screenWidth;
var screenHeight;

// state
/* 0 = normal,
 * 1 = select tile,
 * 2 = select vertex,
 * 3 = select edge,
 * 4 = select location to train,
 * 5 = highlight tiles,
 * 6 = movement mode,
 * 7 = action mode
 */
var globalState = 0;
var globalHighlightFunct = null;
var globalSelectFunct = null;
var globalMinimapState = false;
var globalBuildState = false;
var globalPauseAutoUpdate = false;
var globalDebug = false;
var selectedTile = null;
var selectedVertex = null;
var selectedEdge = null;
var selectedBuilding = null;
var selectedPath = null;
var tDrawRollTokens = true;
var isOverlayShown = false;
var OverlayShownId = "";
var isTradeActive = false;
var isBuildActive = false;
var serverTime = 0;

// nation
var nation = null;
var capitol = null;

// map
var mapX = null;
var mapY = null;
var mapSizes = 50;
var tileMap = [];
var tileLoader = [];
var civLoader = [];

/* MapBlock object constructor. */
function MapBlock()
{
    var o = {valid: false, invalidLOS: false, token: 0,
             map: new Array(mapSizes), buildables: new Array(),
             movemap: new Array(mapSizes*mapSizes)};

    /* Tiles */
    for (var j=0; j < mapSizes; j++) {
        o.map[j] = new Array(mapSizes);
    }

    /* Move map */
    for (var i=0; i < o.movemap.length; i++) {
        o.movemap[i] = 0;
    }

    return o;
}

/* Vect object constructor. */
function Vect(x, y)
{
    return {"x": x, "y": y};
}

/* WorldVect object constructor. */
function WorldVect(i, x, y)
{
    return {"x": x, "y": y, "i": i};
}

/* BlockVect object constructor. */
function BlockVect(bx, by, x, y)
{
    return {"x": x, "y": y, "bx": bx, "by": by};
}

function initMap(w, h)
{
    for (var i=0; i < 4; i++) {
        tileMap[i] = new MapBlock();
    }
}

function getWorldPos(i)
{
    var r = {x: mapX, y: mapY};
    r.x += (i == 0 || i == 2 ? 0 : 1);
    r.y += (i == 0 || i == 1 ? 0 : 1);
    return r;
}

function getiFromWorldPos(x, y)
{
    if (mapX == x) {
        if (mapY == y)
            return 0;
        else if (mapY + 1 == y)
            return 2;
    } else if (mapX + 1 == x) {
        if (mapY == y)
            return 1;
        else if (mapY + 1 == y)
            return 3;
    }
    return -1;
}

function getiFromPos(x, y)
{
    return (x < mapSizes ? 0 : 1) + (y < mapSizes ? 0 : 2);
}

function getPosFromi(i, x, y)
{
    return Vect(x + (i == 0 || i == 2 ? 0 : mapSizes),
                y + (i == 0 || i == 1 ? 0 : mapSizes));
}

function getScreenCoordFromPos(v)
{
    return Vect(outputx(v.x - screenX, v.y - screenY),
                outputy(v.x - screenX, v.y - screenY));
}

function vectToWorldVect(i, v)
{
    var vt = getPosFromi(i, v.x, v.y);
    return WorldVect(getiFromPos(vt.x, vt.y), vt.x % mapSizes, vt.y % mapSizes);
}

function mapVectToScreen(v)
{
    var d = getPosFromi(v.i, v.x, v.y);
    var x = d.x - screenX;
    var y = d.y - screenY;
    d.x = outputx(x, y);
    d.y = outputy(x, y);
    return d;
}

/* Parses a JSON response from the server.
 *
 * json: A decoded object from the server.
 */
function JSONCallback(jsonObj)
{
    /* json error */
    var error = false;
    if (jsonObj.error) {
        error = true;
    } else if (jsonObj.response) {
        var json = jsonObj.response;
        /* Update time. */
        serverTime = jsonObj.time;

        /* Parse capitol and nation data. */
        if (json['nation']) {
            parseNation(json['nation']);
        }

        if (json['capitol']) {
            parseCapitol(json['capitol']);
        }

        if (json['nation']) {
            populateVillageList();
            /* Switch to new capitol. */
            if (json['isNewCapitol'] && nation && capitol &&
                nation.capitol_count - 1 != capitol.number) {
                for (var i=0; i<tileMap.length; i++)
                    tileMap[i].valid = false;
                CapitolSwitch(nation.capitol_count - 1, false);
            }
        }

        /* parse block data */
        var mapUpdated = false;
        for (var i=0; i<tileMap.length; i++) {
            var pos = getWorldPos(i);
            var id = pos.x + '_' + pos.y;
            if (json[id] && (!isBuildActive || json['isBuildResult'])) {
                /* block token */
                if (json[id].token) {
                    tileMap[i].token = json[id].token;
                }
                /* buildable data */
                if (json[id].buildableblock) {
                    error = parseBuildableBlock(i, json[id].buildableblock);
                    mapUpdated = true;
                }
                /* map data */
                if (json[id].mapblock) {
                    error = parseMapBlock(i, json[id].mapblock);
                    tileMap[i].valid = true;
                    tileMap[i].invalidLOS = false;
                    mapUpdated = true;
                }
            }
        }

        /* Remove move path and try delayed actions. */
        if (json['isMoveResult']) {
            if (globalState != 6)
                selectedPath = null;
            /* Attempt to call delayed actions. */
            if (ActionModeData.length > 0) {
                var tmpActions = ActionModeData;
                ActionModeData = new Array();
                for (var i=0; i<tmpActions.length; i++) {
                    ActionModeDo(tmpActions[i].a, tmpActions[i].d,
                                 tmpActions[i].id);
                }
            }
        }

        /* Remove smoke. */
        if (json['isAttackResult']) {
            SmokeData.shift();
        }

        /* Update LOS on an as-needed basis. */
        updateLOSAsNeeded();

        /* Update Minimap and move map. */
        if (mapUpdated) {
            discardPaths();
            updateSelectedBuildable();
            if (globalMinimapState)
                minimapRender();
            MoveModeUpdateMap();
        }

        /* Re-enable trade if this is a trade result. */
        if (json['isTradeResult'])
            tradeIdle();

        /* Re-enable map updates if this is a build result. */
        if (json['isBuildResult']) {
            buildEnable();
        }
    }
    render();
}

/* Parses a Capitol JSON object. */
function parseCapitol(json)
{
    if (!json.nation) return;
    var capChange = false;
    if (!capitol || (json.number != capitol.number)) {
        capChange = true;
    }
    capitol = json;
    /* Update MapBlock. */
    if (capChange && !capitol.disableJump) {
        var xoff = 0;
        var yoff = 0;
        if (json.x < mapSizes/2) xoff = 1;
        if (json.y < mapSizes/2) yoff = 1;
        goMap(json.bx - xoff, json.by - yoff);
        screenX = json.x - Math.round(screenWidth/2) + mapSizes*xoff;
        screenY = Math.floor((json.y - Math.floor(screenHeight/2))/2)*2
                  + mapSizes*yoff;
    }
    /* Update Nation. */
    if (nation && capitol.capitol_count != nation.capitol_count)
        RequestJSON("GET", "/get/capitol", {});
}

/* Parses a Nation JSON Object. */
function parseNation(json)
{
    if (!json.name) return;
    nation = json;
}

/* Parses a MapBlock formatted string.
 *
 * i: The associated tileMap[] index.
 * str: The MapBlock formatted string.
 * */
function parseMapBlock(i, str)
{
    var error = false;
    /* sanity length check */
    var t = str.split(',');
    if (t.length < mapSizes) {
        error = true;
        requestMap(i);
    }

    /* fill map */
    var k = 0;
    for (var l=0; l < mapSizes; l++) {
        for (var j=0; j < mapSizes; j++) {
            var r = t[k++].split(':');
            tileMap[i].map[l][j] = {type: r[0], roll: r[1]};
        }
    }

    return error;
}

/* Parses a BuildableBlock object.
 *
 * i: The associated tileMap[] index.
 * list: A list of Buildable objects.
 */
function parseBuildableBlock(i, list)
{
    /* Count nations's buildables. */
    var count = null;
    if (tileMap[i].buildables.length > 0) {
        count = hashBuildables(i);
    }

    /* Use new data and start autoupdate. */
    tileMap[i].buildables = list;
    launchAutoUpdate();

    /* Re-count buildables and issue LOS update if needed. */
    if (count != null) {
        if (count != hashBuildables(i)) {
            tileMap[i].invalidLOS = true;
        }
    }

    /* Update path if visible. */
    if (globalState == 6)
        MoveModeUpdateMap();
}

/* Constructs a hash of the buildables owned by this nation in tileMap[i]. */
function hashBuildables(i)
{
    if (!capitol || !tileMap[i].valid) {
        return "";
    }
    var hash = "";
    for (var j=0; j < tileMap[i].buildables.length; j++) {
        var b = tileMap[i].buildables[j];
        if (b.n == capitol.nation) {
            hash += b.x + "," + b.y + "," + b.d + "," + b.t + ":";
        }
    }
    return hash;
}

/* Request updated MapBlock data if LOS changes. */
function updateLOSAsNeeded()
{
    var update = false;
    var req = new Array();
    /* Check if a LOS update is needed. */
    for (var i=0; i<tileMap.length; i++) {
        req.push(i);
        if (tileMap[i].invalidLOS == true) {
            update = true;
            break;
        }
    }
    /* Update LOS. */
    if (update) {
        requestBlocks(req, true);
    }
}


/* Go to a specific MapBlock coordinate. */
function goMap(worldX, worldY)
{
    if (worldX == mapX && worldY == mapY) return;

    /* shift */
    if (Math.abs(worldX-mapX) > 1 || Math.abs(worldX-mapX > 1)) {
        tileMap[0].valid = false;
        tileMap[0].req_count = 0;
        tileMap[1].valid = false;
        tileMap[1].req_count = 0;
        tileMap[2].valid = false;
        tileMap[2].req_count = 0;
        tileMap[3].valid = false;
        tileMap[3].req_count = 0;
    } else {
        if (worldX == mapX-1) {
            tileMap[1] = tileMap[0];
            tileMap[3] = tileMap[2];
            tileMap[0] = new MapBlock();
            tileMap[2] = new MapBlock();
            screenX += mapSizes;
        } else if (worldX == mapX+1) {
            tileMap[0] = tileMap[1];
            tileMap[2] = tileMap[3];
            tileMap[1] = new MapBlock();
            tileMap[3] = new MapBlock();
            screenX -= mapSizes;
        }
        if (worldY == mapY-1) {
            tileMap[2] = tileMap[0];
            tileMap[3] = tileMap[1];
            tileMap[0] = new MapBlock();
            tileMap[1] = new MapBlock();
            screenY += mapSizes;
        } else if (worldY == mapY+1) {
            tileMap[0] = tileMap[2];
            tileMap[1] = tileMap[3];
            tileMap[2] = new MapBlock();
            tileMap[3] = new MapBlock();
            screenY -= mapSizes;
        }
    }

    /* Clear selected building.
     * (technically it could be shifted too) */
    selectedBuilding = null;

    /* set position */
    mapX = worldX;
    mapY = worldY;
    
    /* request blocks */
    var req = new Array();
    for (var i=0; i < 4; i++) {
        if (tileMap[i].valid == false) {
            req.push(i);
        }
    }
    requestBlocks(req, true);

    /* Update Minimap if visible. */
    if (globalMinimapState)
        minimapRender();

    /* Update path if visible. */
    if (globalState == 6)
        MoveModeUpdateMap();
}

function moveWest()
{
    screenOffsetX -= TileWidth/3;
    if (screenOffsetX <= -TileWidth + 1) {
        screenOffsetX += TileWidth;
        screenX -= 1;
    }
}

function moveEast()
{
    screenOffsetX += TileWidth/3;
    if (screenOffsetX >= TileWidth - 1) {
        screenOffsetX -= TileWidth;
        screenX += 1;
    }
}

function moveNorth()
{
    screenOffsetY -= TileOffset/2;
    if (screenOffsetY <= -2*TileOffset + 1) {
        screenOffsetY += 2*TileOffset;
        screenY -= 2;
    }
}

function moveSouth()
{
    screenOffsetY += TileOffset/2;
    if (screenOffsetY >= 2*TileOffset - 1) {
        screenOffsetY -= 2*TileOffset;
        screenY += 2;
    }
}

function getTile(x, y)
{
    var i = 0;
    /* determine array */
    if (x >= mapSizes) {
        i += 1;
        x -= mapSizes;
    }   
    if (y >= mapSizes) {
        i += 2;
        y -= mapSizes;
    }
    /* return tile */
    if (!tileMap[i].valid || x < 0 || y < 0 || x >= mapSizes || y >= mapSizes) {
        return {type: 0, roll: -1};
    }
    return tileMap[i].map[y][x];

}

// keyboard

function keyPressCallback(e)
{
    switch (e.keyCode) {
        case 37:
            if (scrollWE != -1) {
                scrollWE = -1;
                moveWest();
                setScroll();
                render();
            }
            break;
            
        case 38:
            if (scrollNS != -1) {
                scrollNS = -1;
                moveNorth();
                setScroll();
                render();
            }
            break;
            
        case 39:
            if (scrollWE != 1) {
                scrollWE = 1;
                moveEast();
                setScroll();
                render();
            }
            break;
            
        case 40:
            if (scrollNS != 1) {
                scrollNS = 1;
                moveSouth();
                setScroll();
                render();
            }
            break;
            
        default:
            return true;
            break;
    }

    return false;
}

function keyReleaseCallback(e)
{
    switch (e.keyCode) {
        case 37:
        case 39:
            scrollWE = 0;
            break;

        case 38:
        case 40:
            scrollNS = 0;
            break;

        default:
            return true;
            break;
    }

    return false;
}

function setScroll()
{
    if (scrollId == null) {
        scrollId = setInterval(updateScroll, scrollDelay);
    }
}

function updateScroll()
{
    if (!scrollWE && !scrollNS) {
        if (scrollId != null) {
            clearInterval(scrollId);
            scrollId = null;
        }
        return;
    }

    /* scroll */
    if (scrollWE == 1) moveEast();
    else if (scrollWE == -1) moveWest();
    if (scrollNS == 1) moveSouth();
    else if (scrollNS == -1) moveNorth();

    updateMapScroll();

    render();
}

function updateMapScroll()
{
    /* update maps */
    if (screenX + screenWidth/2 < mapSizes/3)
        goMap(mapX-1, mapY);
    if (screenX + screenWidth/2 > (5/3)*mapSizes)
        goMap(mapX+1, mapY);
    if (screenY + screenHeight/2 < mapSizes/3)
        goMap(mapX, mapY-1);
    if (screenY + screenHeight/2 > (5/3)*mapSizes)
        goMap(mapX, mapY+1);
}

// toggles
function toggleRollTokens()
{
    tDrawRollTokens = !tDrawRollTokens;
    render();
}

// mouse timers
function updateMouse(e)
{
    if (!mouseActive) return;
    reportUserActivity();

    if (e.pageX != undefined && e.pageY != undefined) {
        mouseX = e.pageX - canvas.offsetLeft;
        mouseY = e.pageY - canvas.offsetTop;
    } else {
        mouseX = e.clientX + document.body.scrollLeft +
            document.documentElement.scrollLeft - canvas.offsetLeft;
        mouseY = e.clientY + document.body.scrollTop +
            document.documentElement.scrollTop - canvas.offsetTop;
    }

    pureMouseX = mouseX;
    pureMouseY = mouseY;

    mouseX += screenOffsetX;
    mouseY += screenOffsetY;

    /* Disable clicks if mouse moves. */
    var xdiff = clickMouseX - pureMouseX;
    var ydiff = clickMouseY - pureMouseY;
    if (!movedMouse && xdiff*xdiff + ydiff*ydiff > 5*5)
        movedMouse = true;

    UICheckState(pureMouseX, pureMouseY);
    updateSelection();
}

function updateSelection()
{
    // set current tile
    var t = getTileCoord(mouseX, mouseY);
    if (!selectedTile || (!t && selectedTile) || t.x != selectedTile.x ||
            t.y != selectedTile.y) {
        selectedTile = t;
        onTileChange();
    }

    // set current vertex
    var v = getVertex();
    if (!selectedVertex || (!v && selectedVertex) ||
            v.x != selectedVertex.x || v.y != selectedVertex.y ||
            v.d != selectedVertex.d) {
        selectedVertex = v;
        onVertexChange();
    }

    // set current edge
    var e = getEdge();
    if (!selectedEdge || (!e && selectedEdge) || e.x != selectedEdge.x ||
            e.y != selectedEdge.y || e.d != selectedEdge.d) {
        selectedEdge = e;
        onEdgeChange();
    }
}

function updateMouseOver()
{
    mouseActive = true;
}

function updateMouseOut()
{
    mouseActive = false;
    selectedTile = null;
    selectedVertex = null;
    selectedEdge = null;
    mouseOutCallback();
    render();
}

/* mouse-based scrolling */
var oldMouseX = 0;
var oldMouseY = 0;
var mouseScrollTimer = null;

function initMouseScroll()
{
    canvas.onmousedown = mouseCallback;
    canvas.onmouseup = mouseOutCallback;
    canvas.onclick = mouseClickCallback;
    
    canvas.touchstart = mouseTouch;
    canvas.touchend = mouseOutCallback;
    canvas.touchmove = updateMouse;
}

/* callbacks */
function mouseCallback()
{
    reportUserActivity();

    /* UI click. */
    if (UIHandleClick(pureMouseX, pureMouseY))
        return;

    /* Hide overlays. */
    if (isOverlayShown)
        hideOverlays();

    /* Build click. */
    if (globalBuildState) {
        BuildModeDo();
        return;
    /* Click on map. */
    }

    /* start mouse scroll */
    if (mouseScrollTimer != null) return;
    mouseScrollTimer = setInterval(mouseScroll, dragDelay);

    clickMouseX = pureMouseX;
    clickMouseY = pureMouseY;
    movedMouse = false;
    oldMouseX = pureMouseX;
    oldMouseY = pureMouseY;

    canvas.style.cursor = 'move';
}

function mouseClickCallback()
{
    /* Do not generate clicks on map scroll events. */
    if (movedMouse) return;

    /* Map click. */
    if (!globalBuildState)
        MapClickCallback();
}

function mouseOutCallback()
{
    if (mouseScrollTimer == null) return;
    mouseScroll();
    clearInterval(mouseScrollTimer);
    mouseScrollTimer = null;
    
    canvas.style.cursor = 'auto';
}

function mouseTouch(e)
{
    updateMouse(e);
    mouseCallback();
}

/* update mouse scroll */
function mouseScroll()
{
    if (oldMouseX == pureMouseX && oldMouseY == pureMouseY) return;
    
    /* get mouse movement */
    var dx = Math.floor(oldMouseX - pureMouseX + screenOffsetX +
                 screenX*TileWidth);
    var dy = Math.floor(oldMouseY - pureMouseY + screenOffsetY +
                 screenY*TileOffset);

    /* move screen */
    screenX = Math.floor(dx/TileWidth);
    screenY = Math.floor(dy/(2*TileOffset))*2;
    screenOffsetX = Math.floor(dx - screenX*TileWidth);
    screenOffsetY = Math.floor(dy - screenY*TileOffset);


    /* render */
    updateMapScroll();  
    render();
    
    /* update old mouse positions */
    oldMouseX = pureMouseX;
    oldMouseY = pureMouseY;
}

/* Selection change callbacks. */
function onTileChange()
{
    if (globalState == 1) {
        render();
    } else if (globalState == 6) {
        /* Update movement path. */
        MoveModeUpdatePath();
        render();
    }
}

function onVertexChange()
{
    if (globalState == 2) {
        render();
    }
}

function onEdgeChange()
{
    if (globalState == 3) {
        render();
    }
}

// tile attributes
var TileWidth = 154;
var TileHeight = 174;
var TileOffset = Math.floor(TileHeight - TileHeight*3/12);
var TileEdge = Math.floor(TileWidth/Math.sqrt(3));

// verticies
var TileVerts = [];
TileVerts[0] = {x: 0, y: TileHeight/2};
TileVerts[1] = {x: TileWidth/2, y: TileEdge/2};
TileVerts[2] = {x: TileWidth/2, y: -TileEdge/2};
TileVerts[3] = {x: 0, y: -TileHeight/2};
TileVerts[4] = {x: -TileWidth/2, y: -TileEdge/2};
TileVerts[5] = {x: -TileWidth/2, y: TileEdge/2};

// edges
var TileEdges = [];
TileEdges[0] = {x: (TileVerts[0].x+TileVerts[1].x)/2, y: (TileVerts[0].y+TileVerts[1].y)/2};
TileEdges[1] = {x: TileWidth/2, y: 0};
TileEdges[2] = {x: (TileVerts[2].x+TileVerts[3].x)/2, y: (TileVerts[2].y+TileVerts[3].y)/2};
TileEdges[3] = {x: (TileVerts[3].x+TileVerts[4].x)/2, y: (TileVerts[3].y+TileVerts[4].y)/2};
TileEdges[4] = {x: -TileWidth/2, y: 0};
TileEdges[5] = {x: (TileVerts[5].x+TileVerts[0].x)/2, y: (TileVerts[5].y+TileVerts[0].y)/2};

// ship rotation
var TileCosine = [Math.cos(-Math.PI/6), Math.cos(-Math.PI/2), Math.cos(Math.PI/6)];
var TileSine = [Math.sin(-Math.PI/6), Math.sin(-Math.PI/2), Math.sin(Math.PI/6)];

// load tiles
var tileSpriteSize = 11;
var tileSprite;
var ImgHighlight;
var ImgAttackHighlight;
var ImgMoveHighlight;
var ImgSmoke;
var ImgFire;
var LogoLoading;
var tokens = [];
var specialTokens = [];
var resourceIcons = [];

// Minimap
var mCanvas;
var mCtx;
var mTileImg;

// loaders
var toload = 0;
var toloadtotal = 0;
var loaders = [];

function loadNext()
{
    if (!toload) return;
    loaders[toloadtotal - toload]();
}

function atload()
{
    toload++;
    toloadtotal++;
    return toloadtotal - 1;
}

function atloaderror()
{
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    ctx.font = "50pt serif";
    ctx.fillStyle = "#fff";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("Infintropolis", canvas.width/2, canvas.height/2 - 50);
    ctx.fillStyle = "#d00";
    ctx.font = "35pt serif";
    ctx.fillText("failed to load.", canvas.width/2, canvas.height/2 + 50);
}

function atloaded()
{
    toload--;
    
    /* draw loading bar */
    if (!initd) {
        ctx.fillStyle = "#fff";
        ctx.strokeStyle = "#fff";
        ctx.lineWidth = 2;
        ctx.strokeRect(canvas.width/3, 3/4*canvas.height, canvas.width/3, 25);
        ctx.fillRect(canvas.width/3, 3/4*canvas.height, (1.0-toload/toloadtotal)*canvas.width/3, 25);
    }

    /* check if fully loaded */
    if (isloaded()) {
        init();
    } else {
        loadNext();
    }
}

function isloaded()
{
    return (toload <= 0);
}

// loading
function loading()
{
    if (initd) return;

    canvas = document.getElementById('canvas');
    ctx = canvas.getContext("2d");
    resize_full_norender();

    // loading message
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    ctx.font = "50pt infbasic, serif";
    ctx.fillStyle = "#fff";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("Infintropolis", canvas.width/2, canvas.height/2 - 50);
    ctx.fillText("is loading...", canvas.width/2, canvas.height/2 + 50);

    // init map
    initMap();

    // load tiles
    tileSprite = loadImg('/img/tiles.png');
    ImgHighlight = loadImg('/img/high.png');
    ImgAttackHighlight = loadImg('/img/high_attack.png');
    ImgMoveHighlight = loadImg('/img/high_move.png');
    ImgSmoke = loadImg('/img/smoke.png');
    ImgFire = loadImg('/img/fire.png');
    LogoLoading = loadImg('/img/logo.png');
    // load tokens
    for (i=0; i<11; i++) {
        tokens[i] = loadImg('/img/tokens/' + (i+2) + '.png');
    }
    for (i=0; i<1; i++) {
        specialTokens[i] = loadImg('/img/tokens/s' + i + '.png');
    }
    // load resource icons
    resourceIcons[0] = loadImg('/img/res/wood2.png');
    resourceIcons[1] = loadImg('/img/res/wool_dark.png');
    resourceIcons[2] = loadImg('/img/res/brick2.png');
    resourceIcons[3] = loadImg('/img/res/wheat.png');
    resourceIcons[4] = loadImg('/img/res/ore.png');
    resourceIcons[5] = loadImg('/img/res/gold.png');
    // Minimap tile image
    mTileImg = loadImg('/img/mtiles.png');
    // create UI buttons
    UIAddButton(UIButton(-134, 5, loadImg('/img/ui/build.png'), 0,
                         function() {showOverlay('#build_overlay');}, 2));
    UIAddButton(UIButton(-88, 5, loadImg('/img/ui/trade.png'), 5,
                         function() {showOverlay('#trade_overlay');}, 2));
    UIAddButton(UIButton(90, 2, loadImg('/img/ui/nation.png'), 4,
                         function() {showOverlay('#nation_overlay')}, 2));
    UIAddButton(UIButton(16, 5, loadImg('/img/ui/map_off.png'), 2,
                         minimapOn, 1));
    UIAddButton(UIButton(16, 5, loadImg('/img/ui/map_on.png'), 3,
                         minimapOff, 1));
    UIAddButton(UIButton(-134, 5, loadImg('/img/ui/cancel.png'), 1,
                         BuildModeCancel, 2));
    UIGroupVisible(0, true);
    UIGroupVisible(2, true);
    UIGroupVisible(4, true);
    UIGroupVisible(5, true);

    initOverlays();

    // load all images
    loadNext();
}

function loadImg(url)
{
    var i = new Image;
    loaders[atload()] = loadImgGen(i, url);
    return i;
}

function loadImgGen(img, url)
{
    return function () {
        img.src = url;
        img.onload = atloaded;
        img.onerror = atloaderror;
    };
}

// init
function init()
{
    // ensure only once
    if (initd) return;

    // init
    canvas = document.getElementById('canvas');
    ctx = canvas.getContext("2d");
    resize_full();
    window.onresize = resize_full;
    canvas.onmousemove = updateMouse;
    canvas.onmouseover = updateMouseOver;
    canvas.onmouseout = updateMouseOut;
    hideText();

    // request server data
    RequestJSON("GET", "/get/capitol", {});

    // keypress
    document.onkeydown = keyPressCallback;
    document.onkeyup = keyReleaseCallback;

    // mouse scroll
    initMouseScroll();

    // init minimap
    minimapInit();

    // inited
    initd = true;
    render();
}

// resize
function resize(w, h)
{
    canvas.width = w;
    canvas.height = h;
    screenWidth = Math.ceil(w/TileWidth);
    screenHeight = Math.ceil(h/TileOffset) + 1;
}

function resize_full()
{
    resize_full_norender();
    render();
}

function resize_full_norender()
{
    resize(window.innerWidth, window.innerHeight);
}

// Render.
function render()
{
    if (!initd) return;

    /* Draw loading animation. */
    if (isNoMapsLoaded()) {
        loadingAnimationStart();
        return;
    } else {
        loadingAnimationStop();
    }

    /* Render map. */
    renderTiles();
    renderSelectedHighlight();
    if (selectedPath)
        renderPath(selectedPath);
    renderPaths();
    renderBuildables();

    switch (globalState) {
        case 0:
        break;

        case 1:
            if (selectedTile) {
                drawHighlightTile(selectedTile.x, selectedTile.y);
            }
        break;

        case 2:
            if (selectedVertex) {
                drawVertex(selectedVertex);
            }
        break;

        case 3:
            if (selectedEdge) {
                drawEdge(selectedEdge);
            }
        break;

        default:
        break;
    }

    DrawSmoke();
    UIRenderButtons(pureMouseX, pureMouseY);
    drawResources();
    if (globalMinimapState == true) {
        minimapDraw();
    }

    if (!isAllMapsLoaded())
        drawLoadingMapText("Loading Map");
}

// Check if pending map requests.
function isAllMapsLoaded()
{
    var r = true;
    for (i = 0; i < tileMap.length; i++) {
        if (!tileMap[i].valid)
            r = false;
    }
    return r;
}

// Check if no maps are valid.
function isNoMapsLoaded()
{
    var r = 0;
    for (i = 0; i < tileMap.length; i++) {
        if (!tileMap[i].valid)
            r++;
    }
    return r == tileMap.length || !capitol;
}

// Draw "Map Loading" text.
function drawLoadingMapText(str)
{
    ctx.font = "22pt infbasic, serif";
    ctx.fillStyle = "#fff";
    ctx.strokeStyle = "#000";
    ctx.lineWidth = 2;
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.strokeText(str, canvas.width/2, 35);
    ctx.fillText(str, canvas.width/2, 35);
}

// render path
function renderPath(path)
{
    if (!path || path.length < 2) return;
    ctx.strokeStyle = "rgba(0,0,0,0.6)";
    ctx.lineWidth = 15;
    ctx.lineCap = "butt";
    var v;

    /* Path. */
    v = mapVectToScreen(path[path.length-1]);
    ctx.beginPath();
    ctx.moveTo(v.x, v.y);
    for (var i=path.length-2; i>0; i--) {
        v = mapVectToScreen(path[i]);
        ctx.lineTo(v.x, v.y);
    }
    var pv = mapVectToScreen(path[0]);
    var theta = Math.atan2(v.x - pv.x, v.y - pv.y);
    var xl = pv.x + Math.sin(theta)*20;
    var yl = pv.y + Math.cos(theta)*20;
    ctx.lineTo(xl + Math.sin(theta)*13, yl + Math.cos(theta)*13);
    ctx.lineTo(xl + Math.sin(theta+Math.PI/8)*15,
               yl + Math.cos(theta+Math.PI/8)*15);
    ctx.lineTo(xl, yl);
    ctx.lineTo(xl + Math.sin(theta-Math.PI/8)*15,
               yl + Math.cos(theta-Math.PI/8)*15);
    ctx.lineTo(xl + Math.sin(theta)*13, yl + Math.cos(theta)*13);
    ctx.moveTo(xl, yl);
    ctx.closePath();
    ctx.stroke();
}

// render highlight tile
function drawHighlightTile(x, y)
{
    ctx.drawImage(ImgHighlight, outputx(x,y) - TileWidth/2, outputy(x,y) - TileHeight/2);
}

// draw shape
function drawShape(context, x, y, shape, strokeColor, fillColor, strokeWidth)
{
    if (!shape) return;
    context.fillStyle = fillColor;
    context.strokeStyle = strokeColor;
    context.lineWidth = strokeWidth;
    context.beginPath();

    context.moveTo(x + shape[0].x, y + shape[0].y);
    for (var i=1; i<shape.length; i++)
        context.lineTo(x + shape[i].x, y + shape[i].y);

    context.closePath();
    context.fill();
    context.stroke();
}

// drawable shapes
var DrawShapes = {
    s: [Vect(8,8),Vect(-8,8),Vect(-8,-4),Vect(0,-11),Vect(8,-4)],
    c: [Vect(13,8),Vect(-12,8),Vect(-12,-9),Vect(-5,-15),Vect(2,-9),Vect(2,-5),
        Vect(13,-5)],
    p: [Vect(6,-8),Vect(6,-4),Vect(2,-4),Vect(2,6),Vect(9,3),
        Vect(12,4),Vect(5,10),Vect(0,12),Vect(-5,10),Vect(-12,4),Vect(-9,3),
        Vect(-2,6),Vect(-2,-4),Vect(-6,-4),Vect(-6,-8)],
    f: [Vect(16,3), Vect(20,-5), Vect(3,-5), Vect(2,-18), Vect(3,-32),
        Vect(0,-32), Vect(-6,-22), Vect(-6,-15), Vect(-3,-7), Vect(-3,-5),
        Vect(-20,-5), Vect(-16,3)]
}

// render middle
function drawMiddle(b, actualBuildable)
{
    if (!b) return;

    // calculate position
    var px = outputx(b.x, b.y);
    var py = outputy(b.x, b.y);

    // set alpha
    if (b.alpha)
        ctx.globalAlpha = b.alpha;

    // draw
    drawShape(ctx, px, py, DrawShapes[b.t], "#" + b.c1, "#" + b.c2, 2.5);

    ctx.globalAlpha = 1.0;

    // draw health
    if (actualBuildable && actualBuildable.hp) {
        ctx.fillStyle = '#c90606';
        ctx.fillRect(px - 25, py + 20, 50, 6);
        ctx.fillStyle = '#144fbc';
        ctx.fillRect(px - 25, py + 20,
                     Math.floor(50 * actualBuildable.hp/actualBuildable.mhp),
                     6);
    }
}

function renderSelectedHighlight()
{
    if (!selectedBuilding || selectedBuilding.d != 'm') return;
    var i = selectedBuilding.mapi;
    var x = selectedBuilding.x - screenX + (i == 0 || i == 2 ? 0 : mapSizes);
    var y = selectedBuilding.y - screenY + (i == 0 || i == 1 ? 0 : mapSizes);
    drawHighlightTile(x, y);
}

// render vertex
function drawVertex(v)
{
    if (!v) return;
    
    // calculate position
    var px = outputx(v.x, v.y) - TileWidth/2;
    var py = outputy(v.x, v.y);

    // handle top and bottom
    if (v.d =='b') {
        py += TileEdge/2;
    } else {
        py -= TileEdge/2;
    }

    // set alpha
    if (v.alpha)
        ctx.globalAlpha = v.alpha;

    // draw
    drawShape(ctx, px, py, DrawShapes[v.t], "#" + v.c1, "#" + v.c2, 2.5);

    ctx.globalAlpha = 1.0;
}

// render edge
function drawEdge(e)
{
    if (!e) return;

    // calculate position
    var px = outputx(e.x, e.y);
    var py = outputy(e.x, e.y);

    if (e.alpha)
        ctx.globalAlpha = e.alpha;
    ctx.lineCap = "round";

    /* draw roads */
    var dx1, dx2, dy1, dy2;
    var rlf1 = 20;
    var rlf2 = 16;
    var rlf3 = 12;
    var rlf4 = rlf1 - rlf2;

    if (e.t == 'r') {
        switch (e.d) {
            case 't':
                dx1 = px + (TileVerts[3].x - TileVerts[4].x)*rlf4/rlf1 + TileVerts[4].x;
                dx2 = px + (TileVerts[3].x - TileVerts[4].x)*rlf2/rlf1 + TileVerts[4].x;
                dy1 = py + (TileVerts[3].y - TileVerts[4].y)*rlf4/rlf1 + TileVerts[4].y;
                dy2 = py + (TileVerts[3].y - TileVerts[4].y)*rlf2/rlf1 + TileVerts[4].y;
            break;

            case 'c':
                dx1 = px - TileWidth/2;
                dy1 = py - (TileEdge*rlf3/rlf1)/2;
                dx2 = px - TileWidth/2;
                dy2 = py + (TileEdge*rlf3/rlf1)/2;
            break;
            
            case 'b':
                dx1 = px + (TileVerts[5].x - TileVerts[0].x)*rlf4/rlf1 + TileVerts[0].x;
                dx2 = px + (TileVerts[5].x - TileVerts[0].x)*rlf2/rlf1 + TileVerts[0].x;
                dy1 = py + (TileVerts[5].y - TileVerts[0].y)*rlf4/rlf1 + TileVerts[0].y;
                dy2 = py + (TileVerts[5].y - TileVerts[0].y)*rlf2/rlf1 + TileVerts[0].y;
            break;
        }

        // draw
        ctx.beginPath();
        ctx.moveTo(dx1, dy1);
        ctx.lineTo(dx2, dy2);
        ctx.closePath();
        ctx.strokeStyle = "#" + e.c1;
        ctx.lineWidth = 8.5;
        ctx.stroke();
        ctx.strokeStyle = "#" + e.c2;
        ctx.lineWidth = 4.0;
        ctx.stroke();
    } else {
        var edge;
        var vert;
        if (e.d == 't') {
            edge = 0;
            px += (TileVerts[3].x - TileVerts[4].x)*0.5 + TileVerts[4].x;
            py += (TileVerts[3].y - TileVerts[4].y)*0.5 + TileVerts[4].y;
        } else if (e.d == 'c') {
            edge = 1;
            px -= TileWidth/2;
        } else if (e.d == 'b') {
            edge = 2;
            px += (TileVerts[5].x - TileVerts[0].x)*0.5 + TileVerts[0].x;
            py += (TileVerts[5].y - TileVerts[0].y)*0.5 + TileVerts[0].y;
        }
        var tx = [16, 20, 3, 2, 3, 0, -6, -6, -3, -3, -20, -16];
        var ty = [3, -5, -5, -18, -32, -32, -22, -15, -7, -5, -5, 3]
        //var tx = [16, 20, 3, 3, -16, -3, -3, -20, -16];
        //var ty = [0, -8, -8, -35, -12, -12, -8, -8, 0]
        ctx.beginPath();
        ctx.moveTo(px + tx[0] * TileCosine[edge] - ty[0] * TileSine[edge],
                   py + ty[0] * TileCosine[edge] + tx[0] * TileSine[edge]);
        for (var i=1; i<tx.length; i++)
            ctx.lineTo(px + tx[i] * TileCosine[edge] - ty[i] * TileSine[edge],
                       py + ty[i] * TileCosine[edge] + tx[i] * TileSine[edge]);
        ctx.closePath();
        ctx.fillStyle = "#" + e.c2;
        ctx.strokeStyle = "#" + e.c1;
        ctx.lineWidth = 2.5;
        ctx.fill();
        ctx.stroke();
    }
    ctx.globalAlpha = 1.0;
}

// render world background
function renderTiles()
{
    if (!ctx) return;

    // clear
    ctx.fillStyle = "#e9d16c";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // draw tiles
    var highlight = false;
    var select = false;
    for (i=-1; i<screenWidth+2; i++) {
        for (j=-2; j<screenHeight+2; j++) {
            if (globalHighlightFunct)
                highlight = globalHighlightFunct(i+screenX, j+screenY);
            if (globalSelectFunct)
                select = globalSelectFunct(i+screenX, j+screenY);
            drawTile(getTile(i+screenX, j+screenY), i, j, highlight, select);
        }
    }
}

// render buildables
function renderBuildables()
{
    // draw buildables
    var drawable = {x: 0, y: 0, d: 'b', c1: "000000", c2: "000000"};
    for (i=0; i<tileMap.length; i++) {
        if (!tileMap[i].valid) continue;
        for (j=0; j<tileMap[i].buildables.length; j++) {
            var build = tileMap[i].buildables[j];
            if (!isBuildableVisable(i, build))
                continue;
            drawable.x = build.x - screenX + (i == 0 || i == 2 ? 0 : mapSizes);
            drawable.y = build.y - screenY + (i == 0 || i == 1 ? 0 : mapSizes);
            drawable.d = build.d;
            drawable.t = build.t;
            drawable.c1 = build.c1;
            drawable.c2 = build.c2;
            drawBuildable(drawable, build);
        }
    }
}

// Draw a tile
function drawTile(tile, x, y, highlight, select)
{
    if (tile == undefined) return;

    var dx = outputx(x,y);
    var dy = outputy(x,y);
    var isSpotHighlight = (select || (highlight &&
                           selectedBuilding && selectedBuilding.d != 'm'));
    if (selectedBuilding && !isSpotHighlight) {
    }
    /* Draw. */
    var yoffset = (highlight && !isSpotHighlight ? 2*TileHeight : 0);
    var yoffset = 0;
    if (tile.roll == -1)
        yoffset += TileHeight;
    ctx.drawImage(tileSprite, TileWidth * tile.type,
                  yoffset, TileWidth, TileHeight,
                  dx - TileWidth/2, dy - TileHeight/2, TileWidth, TileHeight);

    if (tDrawRollTokens && tile.roll > 0) {
        /* circle */
        var color = (tile.roll == 6 || tile.roll == 8) ? "#ad151b" : "#000";
        var numDots = tile.roll - 2;
        ctx.drawImage(tokens[numDots], dx - tokens[numDots].width/2,
                                       dy - tokens[numDots].height/2);
    }
    /* event text */
    if (tDrawRollTokens && tile.type == 9 && tile.roll != -1) {
        ctx.drawImage(specialTokens[0], dx - specialTokens[0].width/2,
                                        dy - specialTokens[0].height/2);
    }
    /* select image */
    if ((highlight || select) && tile.type != 0) {
        var sImg = (select ? ImgAttackHighlight : ImgMoveHighlight);
        ctx.drawImage(sImg, dx - sImg.width/2, dy - sImg.height/2);
    }
    /* draw debug text */
    if (globalDebug) {
        ctx.font = "16pt serif";
        ctx.fillStyle = "#000";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText((x + screenX)%mapSizes + "," +
                     (y + screenY)%mapSizes, dx, dy);
    }
}

// Draw a buildable
function drawBuildable(buildable, actualBuildable)
{
    if (buildable == undefined || buildable.x < -1 || buildable.y < -2 ||
        buildable.x > screenWidth + 2 || buildable.y > screenWidth + 2) return;

    // Check buildable type.
    if (buildable.t == 'r') {
        drawEdge(buildable);
    } else if (buildable.d != 'm') {
        drawVertex(buildable);
    } else {
        drawMiddle(buildable, actualBuildable);
    }
}

// coordinate calculations
function outputy(x,y)
{
    return Math.floor(y*TileOffset) - Math.floor(screenOffsetY);
}

function outputx(x,y)
{
    return Math.floor(x*(TileWidth) + (y%2 ? TileWidth/2 : 0)) - Math.floor(screenOffsetX);
}

// determine which tile a pixel coordinate is within
function getTileCoord(x, y)
{
    var tx;
    var ty;

    // compute coordinates
    var sx = Math.floor(x/TileWidth);
    var lx = x%TileWidth;
    var sy = Math.floor(y/TileOffset);
    var ly = y%TileOffset;

    // determine tile
    if (sy%2 == 0) {
        if (ly > TileHeight/2 - lx/Math.sqrt(3) && ly > TileHeight/2 - (TileWidth-lx)/Math.sqrt(3)) {
            ty = sy + 1;
            tx = sx;
        } else if (lx > TileWidth/2) {
            ty = sy;
            tx = sx + 1;
        } else {
            ty = sy;
            tx = sx;
        }
    } else {
        if (ly < TileEdge/2 + lx/Math.sqrt(3) && ly < TileEdge/2 + (TileWidth-lx)/Math.sqrt(3)) {
            tx = sx;
            ty = sy;
        } else if (lx > TileWidth/2) {
            tx = sx + 1;
            ty = sy + 1;
        } else {
            ty = sy + 1;
            tx = sx;
        }
    }

    return {x: tx, y: ty};
}

// determine vertex mouseover
function getVertex()
{
    if (!selectedTile || !mouseActive) return null;

    var ix = mouseX - outputx(selectedTile.x, selectedTile.y) - screenOffsetX;
    var iy = mouseY - outputy(selectedTile.x, selectedTile.y) - screenOffsetY;

    var selected = -1;
    var dx;
    var dy;

    for (i=0; i<6; i++) {
        dx = ix - TileVerts[i].x;
        dy = iy - TileVerts[i].y;
        if (dx*dx + dy*dy < TileEdge*TileEdge/4) {
            selected = i;
            break;
        }
    }

    if (selected < 0) return null;
    
    var v = {x : 0, y : 0, d : 't', alpha: 0.65, c1: "000", c2: "fff",
             t: globalBuildState};
    v.x = selectedTile.x;
    v.y = selectedTile.y;
    if (selected == 0 || selected == 3) {
        v.y += (selected == 3) ? -1 : 1;
        if (!(v.y%2)) v.x += 1;
    } else if (selected == 1 || selected == 2) {
        v.x += 1;
    }

    v.d = (selected == 2 || selected == 4 || selected == 0) ? 't' : 'b';
    
    return v;
}

// determine edge mouseover
function getEdge()
{
    if (!selectedTile || !mouseActive) return null;

    var ix = mouseX - outputx(selectedTile.x, selectedTile.y) - screenOffsetX;
    var iy = mouseY - outputy(selectedTile.x, selectedTile.y) - screenOffsetY;

    var selected = -1;
    var dx;
    var dy;

    for (i=0; i<6; i++) {
        dx = ix - TileEdges[i].x;
        dy = iy - TileEdges[i].y;
        if (dx*dx + dy*dy < TileEdge*TileEdge/4) {
            selected = i;
            break;
        }
    }

    if (selected < 0) return null;
    
    var v = {x : 0, y : 0, d : 't', alpha: 0.65, c1: "000", c2: "fff",
             t: globalBuildState};
    v.x = selectedTile.x;
    v.y = selectedTile.y;

    switch (selected) {
        case 0:
            v.d = 't';
            if (v.y%2) v.x += 1;
            v.y += 1;
            break;

        case 1:
            v.d = 'c';
            v.x += 1;
            break;

        case 2:
            v.d = 'b';
            if (v.y%2) v.x += 1;
            v.y -= 1;
            break;

        case 3:
            v.d = 't';
            break;

        case 4:
            v.d = 'c';
            break;

        case 5:
            v.d = 'b';
            break;
    }

    return v;
}

/* Determine a list of the visible mapTiles[]. */
function computeVisibleBlocks()
{
    var r = new Array();
    var p = new Array();
    p.push({x: -1, y: -1});
    p.push({x: screenWidth + 2, y: -1});
    p.push({x: -1, y: screenHeight + 2});
    p.push({x: screenWidth + 2, y: screenHeight + 2});

    for (j=0; j<p.length; j++) {
        var i = getiFromPos(p[j].x + screenX, p[j].y + screenY);
        if (r.indexOf(i) == -1)
            r.push(i);
    }
    return r;
}

/* Launches an XMLHttpRequest.
 *
 * Expects a JSON formated string response. The JSON string will be parsed and
 * the callback function will be passed an instance of the object. If the
 * request is not successful the passed object will contain a single member
 * variable 'error' which will be set to true.
 *
 * url: The URL to perform an XMLHttpRequest GET requect.
 * callback: Callback function accepting a JSON-decoded object.
 */
function RequestJSON(method, url, data)
{
    if (method != "GET" && method != "POST") return;
    req = new XMLHttpRequest();
    req.onreadystatechange = genRequestCallback(req, JSONCallback);
    if (capitol && capitol.number && !data['capitol']) {
        data['capitol'] = capitol.number;
    }
    json = "request=" + JSON.stringify(data);
    if (method == "GET") {
        url += "?" + json;
    }
    req.open(method, url, true);
    req.setRequestHeader("Cache-Control", "no-cache");
    req.setRequestHeader("Pragma", "no-cache");
    if (method == "POST") {
        req.setRequestHeader("Content-type",
                             "application/x-www-form-urlencoded");
        req.send(json);
    } else {
        req.send(null);
    }
    globalPauseAutoUpdate = true;
}
/* Generates a JSON request callback.
 *
 * For the internal use of RequestJSON() only.
 * req: XMLHttpRequest object.
 * callback: Callback function accepting a JSON-decoded object.
 */
function genRequestCallback(req, callback)
{
    return function () {
        if (req.readyState == 4) {
            globalPauseAutoUpdate = false;
            if (req.status == 200 && req.responseText != '') {
                var res = JSON.parse(req.responseText);
                if (res.response && res.response.logout) {
                    logout();
                } else {
                    callback(res);
                }
            } else {
                callback({error: true});
            }
            delete req;
        }
    };
}

/* Request block data from the server.
 *
 * blocks: A list of block ids, ex. [0, 1, 2].
 * include_maps: Whether to get MapBlocks with BuildableBlocks.
 */
function requestBlocks(blocks, include_maps)
{
    /* Construct request list. */
    var blockList = new Array();
    for (j=0; j<blocks.length; j++) {
        var i = blocks[j];
        var p = getWorldPos(i);
        p['token'] = tileMap[i].token;
        /* Add block if we are getting map data or have LOS there. */
        if (include_maps || (tileMap[i].valid && p['token'] != 0)) {
            blockList.push(p);
        }
    }
    if (!blockList.length) return;
    /* Send request. */
    var url = include_maps ? "/get/map" : "/get/build";
    RequestJSON("GET", url, {maps: blockList});
}

/* The user interface data.
 *
 * UIButtons: Holds the list of UI buttons.
 * BuildablesTypeMap: Maps buildable types {edge/vertex} => {true/false}.
 */
UIButtons = new Array();
UIBuildablesTypeMap = {r: true, b: true};

/* A user interface button.
 *
 * x: Screen position. Negative values are relative to the right edge.
 * y: Screen position. Negative values are relative to the bottom edge.
 */
function UIButton(x, y, img, group, callback, frames)
{
    if (!frames)
        var frames = 1;
    var o = {x: x, y: y, img: img, callback: callback, group: group,
             enabled: false, active: false, frames: frames, drawx: 0, drawy: 0}

    return o;
}

/* Add a UIButton to the interface. */
function UIAddButton(button)
{
    UIButtons.push(button);
}

/* Enables or disables visibility of a UIButton group.
 * 
 * group: The group ID.
 * visible: Either true or false.
 */
function UIGroupVisible(group, visible)
{
    for (i=0; i<UIButtons.length; i++) {
        if (UIButtons[i].group == group) {
            UIButtons[i].enabled = visible;
        }
    }
}

/* Handles UI button clicks.
 *
 * Returns true if the click is fully handled by the UI.
 */
function UIHandleClick(clickx, clicky)
{
    var x;
    var y;
    var d = 1;
    for (i=0; i<UIButtons.length; i++) {
        if (!UIButtons[i].enabled) continue;
        if (UIButtons[i].active) {
            UIButtons[i].callback();
            return true;
        }
    }
    return false;
}

/* Check if UIButton state has changed. */
function UICheckState(mousex, mousey)
{
    var x;
    var y;
    var d = 1;
    var rerender = false;
    /* Update state. */
    for (i=0; i<UIButtons.length; i++) {
        x = UIButtons[i].drawx + (UIButtons[i].drawx < 0 ? canvas.width : 0);
        y = UIButtons[i].drawy + (UIButtons[i].drawy < 0 ? canvas.height : 0);
        if (mousex > x &&
            mousex < x + UIButtons[i].img.width/UIButtons[i].frames &&
            mousey > y && mousey < y + UIButtons[i].img.height) {
            if (UIButtons[i].enabled && UIButtons[i].active != true)
                rerender = true;
            UIButtons[i].active = true;
        } else {
            if (UIButtons[i].enabled && UIButtons[i].active != false)
                rerender = true;
            UIButtons[i].active = false;
        }
    }
    /* rerender on state changes. */
    if (rerender)
        render();
    return rerender;
}

/* Renders visible UIButton objects to the canvas. */
function UIRenderButtons(mousex, mousey)
{
    var x;
    var y;
    var offset;
    var w;

    var barWidth = drawResources();
    var barLeft = Math.round((canvas.width - barWidth)/2);
    var barRight = Math.round((canvas.width + barWidth)/2);

    if (barWidth < 0) return;

    for (i=0; i<UIButtons.length; i++) {
        if (!UIButtons[i].enabled) continue;
        x = UIButtons[i].x + (UIButtons[i].x < 0 ? barLeft : barRight);
        y = UIButtons[i].y + (UIButtons[i].y < 0 ? canvas.height : 0);
        UIButtons[i].drawx = x;
        UIButtons[i].drawy = y;
        w = UIButtons[i].img.width/UIButtons[i].frames;
        offset = (UIButtons[i].active && UIButtons[i].frames > 1) ? w : 0;
        ctx.drawImage(UIButtons[i].img, offset, 0, w, UIButtons[i].img.height,
                      x, y, w, UIButtons[i].img.height);
    }
}

/* Enable Build Mode.
 *
 * buildType: {s, c, r, b, a}
 */
function BuildModeEnable(buildType)
{
    if (isBuildActive)
        return;
    globalState = (UIBuildablesTypeMap[buildType] ? 3 : 2);
    globalBuildState = buildType;
    selectedVertex = null
    selectedEdge = null
    UIGroupVisible(0, false);
    UIGroupVisible(1, true);
    hideOverlays();
    render();
}

function BuildModeLauncher(buildType)
{
    return function () {BuildModeEnable(buildType);};
}

/* End Build Mode. */
function BuildModeCancel()
{
    globalState = 0;
    selectedTile = null;
    selectedVertex = null;
    selectedEdge = null;
    globalBuildState = false;
    if (!isBuildActive)
        buildEnable();
    UIGroupVisible(0, true);
    UIGroupVisible(1, false);
    render();
}

/* Build a buildable at the currently selected location. */
function BuildModeDo()
{
    if (!globalBuildState || isBuildActive)
        return;
    var selected = (globalState == 2 ? selectedVertex : selectedEdge);
    var extraD = (globalState == 2 ? 'v' : '');
    if (selected) {
        /* Modify selected into a proper buildable object. */
        var x = selected.x + screenX;
        var y = selected.y + screenY;
        i = getiFromPos(x, y);
        selected.x = x % mapSizes;
        selected.y = y % mapSizes;
        selected.t = globalBuildState;
        selected.i = i;
        tileMap[i].buildables.push(selected);
        var block = getWorldPos(i);
        /* Launch build request. */
        RequestJSON("POST", "/set/build",
                    {bx: block.x, by: block.y, x: selected.x, y: selected.y,
                     d: selected.d + extraD, type: selected.t});
        buildDisable();
    }
    launchAutoUpdate();
    BuildModeCancel();
}

/* Logs out the current user. */
function logout()
{
    window.location = "/session?action=logout";
}

/* Update visible BuildableBlocks. */
function requestBuildableBlocks()
{
    var bb = computeVisibleBlocks();
    if (!bb.length) return;
    requestBlocks(bb, false);
}

/* Autoupdate State Variables. */
var autoupdateMinPeriod = 10;
var autoupdateMaxPeriod = 10 * 60;
var autoupdatePeriod = autoupdateMinPeriod;
var autoupdateMovement = false;
var autoupdateTimer = null;

/* Auto-update BuildableBlocks callback. */
function autoupdateBuildableBlocks()
{
    clearAutoUpdate();
    if (!globalPauseAutoUpdate)
        requestBuildableBlocks();
    if (autoupdateMovement == true) {
        autoupdatePeriod = autoupdateMinPeriod;
    } else {
        autoupdatePeriod = autoupdateMinPeriod + 3 * autoupdatePeriod / 2;
        if (autoupdatePeriod > autoupdateMaxPeriod)
            autoupdatePeriod = autoupdateMaxPeriod;
    }
    autoupdateMovement = false;
    launchAutoUpdate();
}

/* Launch an Auto-update. */
function launchAutoUpdate()
{
    clearAutoUpdate();
    autoupdateTimer = setTimeout(autoupdateBuildableBlocks,
                                 autoupdatePeriod * 1000);
}

/* Clear Auto-update timer. */
function clearAutoUpdate()
{
    if (autoupdateTimer != null) {
        clearTimeout(autoupdateTimer);
        autoupdateTimer = null;
    }
}

/* Reset Auto-update timer. */
function resetAutoUpdate()
{
    autoupdatePeriod = autoupdateMinPeriod;
    launchAutoUpdate();
}

/* Report user activity. */
function reportUserActivity()
{
    autoupdateMovement = true;
    if (autoupdatePeriod != autoupdateMinPeriod) {
        autoupdateBuildableBlocks();
    }
}

/* Move 1 step in Tile Coordinates.
 *
 * x: X part of hex coordinate.
 * y: Y part of hex coordinate.
 * d: Direction where 0 is east and increments counter-clockwise.
 */
function stepHexCoord(x, y, d)
{
    out = Vect(x, y);
    if (d == 0) {
        out.x++;
        return out;
    } else if (d == 3) {
        out.x--;
        return out;
    } else if (d == 1 || d == 2) {
        out.y--;
    } else if (d == 4 || d == 5) {
        out.y++;
    }
    if (y%2 == 0 && (d == 2 || d == 4)) {
        out.x--;
    } else if (y%2 && (d == 1 || d == 5)) {
        out.x++;
    }
    return out;
}

/* Get tile coordinates surrounding a Buildable.
 *
 * t: Is edge (true) or is vertex (false).
 * x: X part of hex coordinate.
 * y: Y part of hex coordinate.
 * d: Building position ([t,b] or [t,c,b]).
 */
function tilesSurroundingBuildable(t, x, y, d)
{
    if (t) {
        /* edge */
        switch (d) {
            case 't':
                return [Vect(x, y), stepHexCoord(x, y, 2)];
            break;

            case 'c':
                return [Vect(x, y), stepHexCoord(x, y, 3)];
            break;

            case 'b':
                return [Vect(x, y), stepHexCoord(x, y, 4)];
            break;
        }
    } else {
        /* vertex */
        switch (d) {
            case 't':
                return [Vect(x, y), stepHexCoord(x, y, 2),
                        stepHexCoord(x, y, 3)];
            break;

            case 'b':
                return [Vect(x, y), stepHexCoord(x, y, 4),
                        stepHexCoord(x, y, 3)];
            break;
        }
    }
    return [];
}

/* Get list of tiles surrounding the given tile. */
function tilesSurroundingTile(x, y)
{
    if (y % 2) {
        return [Vect(x+1, y), Vect(x+1, y-1), Vect(x, y-1), Vect(x-1, y),
                Vect(x, y+1), Vect(x+1, y+1)];
    } else {
        return [Vect(x+1, y), Vect(x, y-1), Vect(x-1, y-1), Vect(x-1, y),
                Vect(x-1, y+1), Vect(x, y+1)];
    }
}

/* Checks if the buildable is adjacent to a visable tile.
 *
 * Returns true if an adjacent tile is visible, false otherwise.
 */
function isBuildableVisable(i, bld)
{
    if (bld.d != 'm') {
        st = tilesSurroundingBuildable((bld.t == 'r'),
                                       bld.x, bld.y, bld.d);
    } else {
        st = [Vect(bld.x, bld.y)]
    }

    for (var j=0; j<st.length; j++) {
        v = getPosFromi(i, st[j].x, st[j].y);
        t = getTile(v.x, v.y);
        if (t.roll != -1)
            return true;
    }
    return false;
}

/* Loading Animation. */
loadingAnimation = {t1: 0, enabled: false, theta: 0, overlay: false};

function loadingAnimationStart()
{
    if (loadingAnimation.enabled == false) {
        loadingAnimation.theta = 0.0;
        loadingAnimation.t1 = setInterval(loadingAnimationDraw, 30);
        loadingAnimation.enabled = true;
        if (isOverlayShown) {
            loadingAnimation.overlay = OverlayShownId;
            hideOverlays();
        } else {
            loadingAnimation.overlay = false;
        }
    }
}

function loadingAnimationStop()
{
    if (loadingAnimation.enabled == true) {
        clearInterval(loadingAnimation.t1);
        loadingAnimation.enabled = false;
        if (loadingAnimation.overlay != false) {
            showOverlay(loadingAnimation.overlay);
        }
    }
}


function loadingAnimationDraw()
{
    ctx.save()
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.translate(canvas.width/2, canvas.height/2);
    ctx.rotate(loadingAnimation.theta)
    loadingAnimation.theta += Math.PI/20;
    ctx.drawImage(LogoLoading, -LogoLoading.width/2, -LogoLoading.height/2);
    ctx.restore();
    drawLoadingMapText("Loading World");
    if (loadingAnimation.theta > 2*Math.PI) {
        if (isOverlayShown)
            hideOverlays();
        loadingAnimation.theta -= 2*Math.PI;
    }
}

function loadingAnimationRandomX()
{
    return ctx.canvas.width/2 * Math.random() + ctx.canvas.width/4;
}

function loadingAnimationRandomY()
{
    return ctx.canvas.height/2 * Math.random() + ctx.canvas.height/4;
}

/* Render resource bar. */
function drawResources()
{
    if (!capitol || capitol.resources.length < 1) {
        drawLoadingMapText("Loading Capitol");
        return -1;
    }

    /* Set font style. */
    ctx.font = "16pt infnumbers, serif";
    ctx.lineWidth = 1;
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";

    /* Settings. */
    var w = 25;
    var wPadding = 6;
    var padding = 50;

    /* Calculate width. */
    var txtWidth = [];
    var totalWidth = 0;
    var totalHeight = 0;
    for (var i=0; i<resourceIcons.length; i++) {
        txtWidth[i] = ctx.measureText(capitol.resources[i]).width;
        totalWidth += resourceIcons[i].width + txtWidth[i] + padding +
                      2*wPadding;
        if (resourceIcons[i].height > totalHeight)
            totalHeight = resourceIcons[i].height;
    }
    totalWidth -= padding + wPadding*2;

    /* Draw resources. */
    var offset = canvas.width/2 - totalWidth/2;
    ctx.fillStyle = "rgba(0, 0, 0, 1.0)";
    ctx.strokeStyle = "#ddd";
    ctx.lineWidth = 1;
    ctx.fillRect(offset - wPadding*2, w - totalHeight/2 - wPadding,
                 totalWidth + wPadding*4, totalHeight + wPadding*2);
    ctx.strokeRect(offset - wPadding*2, w - totalHeight/2 - wPadding,
                   totalWidth + wPadding*4, totalHeight + wPadding*2);
    ctx.fillStyle = "#fff";
    for (var i=0; i<resourceIcons.length; i++) {
        ctx.drawImage(resourceIcons[i], Math.round(offset),
                      Math.round(w - resourceIcons[i].height/2));
        ctx.fillText(capitol.resources[i],
                     offset + resourceIcons[i].width + wPadding*2, w);
        offset += resourceIcons[i].width + txtWidth[i] + wPadding + padding;
    }

    return totalWidth;
}

/* Init Minimap. */
function minimapInit()
{
    mCanvas = document.getElementById('minimap');
    mCtx = mCanvas.getContext("2d");
    mCanvas.width = Math.ceil(2*mapSizes*10 + 5 + 6);
    mCanvas.height = Math.ceil(2*mapSizes*7 + 4 + 6);
}

/* Render Minimap. */
function minimapRender()
{
    mCtx.fillStyle = "rgba(0, 0, 0, 1.0)";
    mCtx.fillRect(0, 0, mCanvas.width, mCanvas.height);

    /* Draw tiles. */
    for (var i=0; i<2*mapSizes; i++) {
        for (var j=0; j<2*mapSizes; j++) {
            var tile = getTile(i, j);
            if (!tile.type)
                continue;
            mCtx.drawImage(mTileImg, 10 * tile.type,
                  (tile.roll == -1 ? 11 : 0), 10, 11,
                  i*10 + (j%2 ? 5 : 0) + 3, j*7 + 3, 10, 11);
        }
    }
    /* Draw buildables. */
    for (var s=0; s<2; s++) {
        for (var i=0; i<tileMap.length; i++) {
            if (!tileMap[i].valid) continue;
            for (var j=0; j<tileMap[i].buildables.length; j++) {
                var build = tileMap[i].buildables[j];
                if ((s && (build.t == 'r' || build.t == 'b')) ||
                    (!s && (build.t != 'r' && build.t != 'b')) ||
                    !isBuildableVisable(i, build))
                    continue;
                var v = getPosFromi(i, build.x, build.y);
                var x = v.x*10 + (v.y%2 ? 5 : 0) + 3;
                var y = v.y*7 + 3;
                if (build.t == 'r' || build.t == 'b') {
                    mCtx.beginPath();
                    if (build.d == 't') {
                        mCtx.moveTo(x + 4, y);
                        mCtx.lineTo(x, y + 2);
                    } else if (build.d == 'c') {
                        mCtx.moveTo(x, y + 3);
                        mCtx.lineTo(x, y + 7);
                    } else if (build.d =='b') {
                        mCtx.moveTo(x, y + 8);
                        mCtx.lineTo(x + 4, y + 10);
                    }
                    mCtx.closePath();
                    mCtx.lineWidth = 4;
                    mCtx.strokeStyle = "#" + build.c1;
                    mCtx.stroke();
                    mCtx.strokeStyle = "#" + build.c2;
                    mCtx.lineWidth = 1;
                    mCtx.stroke();
                } else {
                    var yoff = (build.d == 't' ? 3 : 7);
                    var xoff = 0;
                    if (build.d == 'm') {
                        yoff = 5;
                        xoff = 5;
                    }
                    mCtx.fillStyle = "#" + build.c2;
                    mCtx.strokeStyle = "#" + build.c1;
                    mCtx.lineWidth = 2;
                    mCtx.fillRect(x - 2 + xoff, y - 2 + yoff, 4, 4);
                    mCtx.strokeRect(x - 2 + xoff, y - 2 + yoff, 4, 4);
                }
            }
        }
    }
}

/* Overlay Minimap on Screen. */
function minimapDraw()
{
    var width = Math.round(canvas.width / 2);
    var height = Math.round(mCanvas.height / mCanvas.width * width);
    var scale = width / mCanvas.width;
    if (width > mCanvas.width) {
        width = mCanvas.width;
        height = mCanvas.height;
        scale = 1;
    }
    var x = Math.round(canvas.width/2 - width/2);
    var y = Math.round(canvas.height/2 - height/2);
    ctx.drawImage(mCanvas, x, y, width, height);
    var mx = Math.round(x+((screenX+screenOffsetX/TileWidth)*10
             + (screenY%2 ? 5 : 0))*scale) + 0.5;
    var my = Math.round(y+(screenY+screenOffsetY/TileOffset)*7*scale) + 0.5;
    var mw = Math.round(screenWidth*10*scale) + 2;
    var mh = Math.round(screenHeight*7*scale) + 2;
    ctx.lineWidth = 1;
    ctx.strokeStyle = "#000";
    ctx.strokeRect(mx + 1, my + 1, mw, mh);
    ctx.strokeStyle = "#fff";
    ctx.strokeRect(mx, my, mw, mh);
}

function minimapOn()
{
    UIGroupVisible(2, false);
    UIGroupVisible(3, true);
    globalMinimapState = true;
    minimapRender();
    render();
}

function minimapOff()
{
    UIGroupVisible(3, false);
    UIGroupVisible(2, true);
    globalMinimapState = false;
    render();
}

/* Perform trade. */
function tradePerform()
{
    var form = document.getElementById('trade_form');
    var tradeFrom = getSelectedRadioButton(form.trade);
    var tradeFor = getSelectedRadioButton(form.tradef);

    /* Close overlay. */
    if (isTradeActive)
        return;
    tradeBusy();
    /* Launch trade. */
    if (tradeFor && tradeFrom) {
        RequestJSON("POST", "/set/trade",
                    {"from": tradeFrom, "for": tradeFor});
        globalPauseAutoUpdate = false;
    }
}

/* Get the selected radio button from an HTML form input. */
function getSelectedRadioButton(group)
{
    for (var i=0; i<group.length; i++) {
        if (group[i].checked) {
            return group[i].value;
        }
    }
    return null;
}

/* Set trade busy. */
function tradeBusy()
{
    var arrow = document.getElementById('trade_arrow');
    arrow.setAttribute("class", "trade_arrow_hidden");
    isTradeActive = true;
}

/* Set trade idle. */
function tradeIdle()
{
    var arrow = document.getElementById('trade_arrow');
    arrow.setAttribute("class", "");
    isTradeActive = false;
}

/* Populate village list. */
function populateVillageList()
{
    if (!nation || !capitol) return;

    /* Set title. */
    var title = document.getElementById('nation_title_text');
    title.innerHTML = nation.name;

    /* Populate list. */
    var str = "";
    var j = capitol.number;
    var html = document.getElementById('village_list');
    for (var i=0; i<nation.capitol_names.length; i++) {
        str += "<a href=\"javascript:void(0);\"";
        if (capitol && capitol.number == j)
            str += " class=\"village_current\"";
        else
            str += " class=\"village_noncurrent\"";
        str += " onclick=\"CapitolSwitch(" + j +
               ", false);\"><span>" + nation.capitol_names[j] +
               "</span></a>\n";
        j++;
        if (j >= nation.capitol_names.length)
            j -= nation.capitol_names.length;
    }
    html.innerHTML = str;
}

/* Create a new Capitol. */
function CapitolNew()
{
    if (!nation) return;
    var name = document.getElementById('rename_form').rename.value;
    RequestJSON("POST", "/set/nation",
                {"name": name, "new": true});
    globalPauseAutoUpdate = false;
    showOverlay('#nation_overlay');
}

/* Launch Capitol Rename. */
function CapitolRenameLaunch()
{
    if (!capitol) return;
    document.getElementById('rename_form').rename.value = capitol.name;
    document.getElementById('rename_action').onclick = CapitolRename;
    showOverlay('#rename_overlay');
    return false;
}

/* Launch New Capitol Name. */
function CapitolNewLaunch()
{
    if (!capitol) return;
    document.getElementById('rename_form').rename.value = "";
    document.getElementById('rename_action').onclick = CapitolNew;
    showOverlay('#rename_overlay');
    return false;
}

/* Rename the current Capitol. */
function CapitolRename()
{
    if (!nation || !capitol) return;
    var name = document.getElementById('rename_form').rename.value;
    RequestJSON("POST", "/set/nation",
                {"name": name, "number": capitol.number});
    globalPauseAutoUpdate = false;
    showOverlay('#nation_overlay');
}

/* Switch to a Capitol. */
function CapitolSwitch(num, disableJump)
{
    if (!capitol || num == null) return;
    globalState = 0;
    capitol = null;
    RequestJSON("GET", "/get/capitol", {"capitol": num,
                                        "disableJump": disableJump});
    render();
}

/* Enable and Disable building. */
function buildEnable()
{
    $(".build_image").removeClass("hidden");
    isBuildActive = false;
}

function buildDisable()
{
    $(".build_image").addClass("hidden");
    isBuildActive = true;
}

/* Overlay Control. */
function initOverlays() {

    var settings = {
        speed: 'fast',
        load: false,
        closeOnClick: false,
        closeOnEsc: false,
        top: '15%',
        api: true
    };

    $.each($(".overlay"), function(i, v){$(v).overlay(settings);});
}

function showOverlay(id)
{
    var api = $(id).overlay();
    if (api.isOpened()) {
        hideOverlays();
    } else {
        api.load();
        isOverlayShown = true;
        OverlayShownId = id;
    }
}

function hideOverlays()
{
    $.each($(".overlay"), function(i, v){$(v).overlay().close();})
    isOverlayShown = false;
}

function hideText()
{
    document.getElementById("font_pull").setAttribute("class", "fonts_hide");
}

/* Get selected buildable. */
function getSelectedBuildable()
{
    if (!selectedTile) return;

    var selected = selectedTile;
    if (selectedVertex)
        selected = selectedVertex;
    var x = selected.x + screenX;
    var y = selected.y + screenY;
    var d = (selectedVertex ? selected.d : 'm');
    i = getiFromPos(x, y);
    x = x % mapSizes;
    y = y % mapSizes;
    if (!tileMap[i].valid)
        return null;

    return getBuildableAt(i, x, y, d);
}

function getBuildableAt(i, x, y, d)
{
    if (i < 0 || i >= tileMap.length) return null;
    /* Loop though all non-road buildables. */
    var b;
    for (var j=0; j<tileMap[i].buildables.length; j++) {
        b = tileMap[i].buildables[j];
        if (b.x == x && b.y == y && b.d == d && !UIBuildablesTypeMap[b.t]) {
            b.mapi = i;
            b.mapBlockVect = getWorldPos(i);
            return b;
        }
    }
    return null;
}

/* Map click. */
function MapClickCallback()
{
    if (!nation || !capitol)
        return;

    /* Highlight states. */
    if (globalHighlightFunct != null && selectedTile) {
        var t = Vect(selectedTile.x + screenX, selectedTile.y + screenY);
        if (globalHighlightFunct(t.x, t.y)) {
            /* TrainMode */
            if (globalState == 4) {
                globalHighlightFunct = TileListHighlighter([t]);
                TrainModeLaunch(t.x, t.y);
            /* MoveMode */
            } else if (globalState == 6) {
                if (MoveModeDo(t.x, t.y)) {
                    globalState = 0;
                    globalHighlightFunct = null;
                }
            }
            render();
            return;
        } else {
            /* Un-highlight. */
            globalState = 0;
            globalHighlightFunct = null;
            render();
        }
    }

    /* Action Mode. */
    if (globalSelectFunct != null && selectedTile) {
        t = Vect(selectedTile.x + screenX, selectedTile.y + screenY);
        if (globalSelectFunct(t.x, t.y)) {
            /* Do action. */
            var di = getiFromPos(t.x, t.y);
            if (ActionModeStart) {
                var abv = Vect(ActionModeStart.bx, ActionModeStart.by);
                var ax = ActionModeStart.x;
                var ay = ActionModeStart.y;
                var dbv = getWorldPos(di);
                ActionModeDo(BlockVect(abv.x, abv.y, ax, ay),
                             BlockVect(dbv.x, dbv.y,
                                       t.x % mapSizes, t.y % mapSizes),
                             selectedBuilding.id);
            }
        } else {
            /* Un-select. */
            globalSelectFunct = null;
            ActionModeStart = null;
            render();
        }
    }


    if (globalState == 0) {
        /* Building is of a different nation. */
        var b = getSelectedBuildable();
        if (!b || b.n != nation.name) {
            if (selectedBuilding) {
                selectedBuilding = null;
                render();
            }
            return;
        }

        /* Building is in a different village. */
        if (b.i >= 0 && b.i != capitol.number && b.d != 'm') {
            popAskConfirm("Govern village " + nation.capitol_names[b.i] + "?",
                          function() {CapitolSwitch(b.i, true);});
            return;
        }

        /* Building is of current nation and village. */
        setSelectedBuilding(b, b.mapi);

        /* Buildable is a port. */
        if (b.t == 'p')
            TrainModeEnable();

        /* Buildable is a ship. */
        if (b.d == 'm')
            MoveModeEnable();
    }
}

/* Set selected buildable. */
function setSelectedBuilding(buildable, i)
{
    selectedBuilding = buildable;
    selectedBuilding.mapi = i;
    selectedBuilding.mapBlockVect = getWorldPos(i);
}

/* Update selected buildable. */
function updateSelectedBuildable()
{
    if (!selectedBuilding) return;

    for (var i=0; i<tileMap.length; i++) {
        if (!tileMap[i].valid) continue;
        var buildables = tileMap[i].buildables;
        for (var j=0; j<buildables.length; j++) {
            if (buildables[j].t == selectedBuilding.t &&
                buildables[j].id == selectedBuilding.id) {
                setSelectedBuilding(buildables[j], i);
                return;
            }
        }
    }
    selectedBuilding = null;
}

/* Is tile water? */
function isWater(tile)
{
    return tile == 1 || tile == 10;
}

/* Does tile have a ship on it? */
function isOpenTile(x, y, visableOnly)
{
    var i = getiFromPos(x, y);
    x = x%mapSizes;
    y = y%mapSizes;
    if (!tileMap[i].valid) return false;
    for (j=0; j<tileMap[i].buildables.length; j++) {
        var build = tileMap[i].buildables[j];
        if (build.x == x && build.y == y && build.d == 'm' &&
            (!visableOnly || isBuildableVisable(i, build)))
            return false;
    }
    return true;
}

/* Enable TrainMode. */
function TrainModeEnable(type, level)
{
    if (!selectedBuilding) return;

    /* Get surrounding water tiles. */
    var p = getPosFromi(selectedBuilding.mapi, selectedBuilding.x,
                        selectedBuilding.y);
    var posTiles = tilesSurroundingBuildable(false,
                                             p.x,
                                             p.y,
                                             selectedBuilding.d);
    var posVects = Array();
    for (var j=0; j<posTiles.length; j++) {
        var t = getTile(posTiles[j].x, posTiles[j].y);
        if (isWater(t.type))
            posVects.push(posTiles[j]);
    }

    /* Setup global state and highlighter. */
    globalState = 4;
    globalHighlightFunct = TileListHighlighter(posVects);
    render();

    /* Single build option, do build. */
    if (posVects.length == 0) {
        return;
    } else if (posVects.length == 1) {
        TrainModeLaunch(posVects[0].x, posVects[0].y);
    } else {
        /* Multiple build options, start choose mode. */
        hideOverlays();
    }
}

/* Launch TrainMode overlay. */
function TrainModeLaunch(x, y) {
    TrainModeData.pos = Vect(x, y);

    /* Launch specific build mode depending on circumstance. */
    var pi = getiFromPos(x, y);
    var build = getBuildableAt(pi, x % mapSizes, y % mapSizes, 'm');

    if (!build) {
        showOverlay('#train_overlay');
    } else if (nation && build.n == nation.name) {
        showOverlay('#cargo_overlay');
    } else if (build.n) {
        /* Enemy ship here. */
    }
}

var TrainModeData = {
    pos: null
};

/* Send Training request to server. */
function TrainModeDo(type, level)
{
    globalState = 0;
    globalHighlightFunct = null;
    hideOverlays();
    if (!TrainModeData.pos) return;
    var i = getiFromPos(TrainModeData.pos.x, TrainModeData.pos.y);
    var x = TrainModeData.pos.x % mapSizes;
    var y = TrainModeData.pos.y % mapSizes;
    var block = getWorldPos(i);
    TrainModeData.pos = null;
    var b = {x: x, y: y, d: 'm', n: null, t: type, c1: "000", c2: "fff"};
    tileMap[i].buildables.push(b);
    RequestJSON("POST", "/set/build",
                {bx: block.x, by: block.y, x: x, y: y,
                 d: 'm', type: type});
    render();
}

/* Generate highlight function for TrainMode. */
function TileListHighlighter(posVects)
{
    return function(x, y) {
        return TileHighlighter(x, y, posVects);
    }
}

/* Highlight function for TrainMode. */
function TileHighlighter(x, y, posVects)
{
    for (var j=0; j<posVects.length; j++) {
        if (posVects[j].x == x && posVects[j].y == y)
            return true;
    }
    return false;
}

/* Show confirm dialogue. */
function popAskConfirm(question, funct)
{
    document.getElementById('confirm_title').innerHTML = question;
    document.getElementById('confirm_action').onclick = function() {
        hideOverlays();
        funct();
    };
    showOverlay('#confirm_overlay');
    return false;
}

/* Is position a start of a move path? */
function isMovePathStart(bx, by, x, y)
{
    for (var i=0; i<DrawPaths.length; i++) {
        var fp = DrawPaths[i][DrawPaths[i].length - 1];
        if (fp.bx == bx && fp.by == by && fp.x == x && fp.y == y)
            return true;
    }
    return false;
}

/* Enable MoveMode. */
function MoveModeEnable()
{
    if (!selectedBuilding) return;
    if (isMovePathStart(selectedBuilding.mapBlockVect.x,
                        selectedBuilding.mapBlockVect.y,
                        selectedBuilding.x, selectedBuilding.y)) {
        selectedBuilding = null;
    } else {
        /* Setup global state and highlighter. */
        globalState = 6;
        globalHighlightFunct = MoveModeHighlighter;
        MoveModeUpdateMap();
    }
    render();
}

var MoveModePath = null;
var DrawPaths = new Array();

/* Render all paths. */
function renderPaths()
{
    for (var i=0; i<DrawPaths.length; i++) {
        var path = DrawPaths[i];
        for (var j=0; j<path.length; j++) {
            path[j].i = getiFromWorldPos(path[j].bx, path[j].by);
            if (path[j].i < 0) break;
        }
        renderPath(path);
    }
}

/* Discard unused paths. */
function discardPaths()
{
    var newPaths = new Array();
    for (var i=0; i<DrawPaths.length; i++) {
        var pos = DrawPaths[i][DrawPaths[i].length - 1];
        var pi = getiFromWorldPos(pos.bx, pos.by);
        if (pi < 0) continue;
        if (getBuildableAt(pi, pos.x, pos.y, 'm'))
            newPaths.push(DrawPaths[i]);
    }
    DrawPaths = newPaths;
}

/* Generate move mode highlighter function. */
function MoveModeHighlighter(x, y)
{
    var i = getiFromPos(x, y);
    x = x % mapSizes;
    y = y % mapSizes;
    return tileMap[i].valid && tileMap[i].movemap[x*mapSizes + y] > 0;
}

/* Perform move. */
function MoveModeDo(x, y)
{
    if (!selectedPath || selectedPath.length < 2) {
        selectedBuilding = null;
        globalSelectFunct = null;
    }

    if (!selectedBuilding || !selectedPath || selectedBuilding.d != 'm' ||
        selectedPath.length < 2)
        return (!selectedBuilding || selectedBuilding.d != 'm');

    /* Construct path. */
    var mpath = new Array();
    for (var j=selectedPath.length-1; j>=0; j--) {
        var b = getWorldPos(selectedPath[j].i);
        var v = {bx: b.x, by: b.y, x: selectedPath[j].x, y: selectedPath[j].y};
        mpath.push(v);
    }

    /* Add path to draw list. */
    var dpath = new Array();
    for (var j=0; j<selectedPath.length; j++) {
        var b = getWorldPos(selectedPath[j].i);
        var v = {bx: b.x, by: b.y, x: selectedPath[j].x, y: selectedPath[j].y};
        dpath.push(v);
    }
    DrawPaths.push(dpath);

    /* Update LOS. */
    var blocks = new Array();
    for (var j=0; j<tileMap.length; j++) {
            blocks.push(getWorldPos(j));
    }

    /* Send request. */
    TrainModeData.pos = null;
    RequestJSON("POST", "/set/move", {path: mpath, maps: blocks});

    /* Chain Action Mode. */
    if (tileMap[selectedPath[0].i].movemap[selectedPath[0].x*mapSizes
                                           + selectedPath[0].y] > 1)
        ActionModeInit(selectedPath[0].i, selectedPath[0].x, selectedPath[0].y);
    else
        globalSelectFunct = null;

    selectedPath = null;
    if (!ActionModeStart)
        selectedBuilding = null;
    return true;
}

/* Calculate movement map. */
function MoveModeUpdateMap()
{
    if (globalState != 6 || !selectedBuilding || selectedBuilding.d != 'm')
        return;

    /* Clear all movemaps. */
    for (var i=0; i<tileMap.length; i++) {
        if (!tileMap[i].valid) continue;
        for (var j=0; j<tileMap[i].movemap.length; j++)
            tileMap[i].movemap[j] = 0;
    }

    var block = selectedBuilding.mapBlockVect;
    var ib = getiFromWorldPos(block.x, block.y);
    if (ib < 0) return;

    /* Get up to date buildable action count. */
    var b = getBuildableAt(ib, selectedBuilding.x, selectedBuilding.y,
                           selectedBuilding.d)
    if (!b || !b.act) return;
    var actions = b.act;

    /* Recursively create map. */
    tileMap[ib].movemap[selectedBuilding.x*mapSizes + selectedBuilding.y] = 999;
    var s = tilesSurroundingTile(selectedBuilding.x, selectedBuilding.y);
    for (var j=0; j<s.length; j++)
        MoveModeRecurse(ib, s[j].x, s[j].y, b.act);
    MoveModeUpdatePath();

    /* Start Action Mode. */
    ActionModeInit(ib, selectedBuilding.x, selectedBuilding.y);
}

function MoveModeRecurse(i, x, y, count)
{
    /* Wrap coordinates. */
    if (x < 0) {
        i -= 1;
        x += mapSizes;
    } else if (x >= mapSizes) {
        i += 1;
        x -= mapSizes;
    }
    if (y < 0) {
        i -= 2;
        y += mapSizes;
    } else if (y >= mapSizes) {
        i += 2;
        y -= mapSizes;
    }
    if (i < 0 || i > 3 || !tileMap[i].valid) return;

    /* Check for land or visable collision. */
    var p = getPosFromi(i, x, y);
    var t = getTile(p.x, p.y);
    if (!isWater(t.type) || !isOpenTile(p.x, p.y, true)) return;

    /* Update map. */
    var index = x*mapSizes + y;
    if (count <= tileMap[i].movemap[index]) return;
    tileMap[i].movemap[index] = count--;
    if (count <= 0) return;

    /* Recurse. */
    var s = tilesSurroundingTile(x, y);
    for (var j=0; j<s.length; j++)
        MoveModeRecurse(i, s[j].x, s[j].y, count);
    MoveModeUpdatePath();
}

/* Calculate movement path. */
function MoveModeUpdatePath()
{
    /* Check that we are in a pathable location. */
    if (!selectedTile) return;
    var x = selectedTile.x + screenX;
    var y = selectedTile.y + screenY;
    var i = getiFromPos(x, y);
    x = x%mapSizes;
    y = y%mapSizes;
    if (tileMap[i].movemap[x*mapSizes + y] <= 0) {
        selectedPath = null;
        return;
    }

    /* Construct path. */
    var tmpPath = new Array();
    var v = {i: i, x: x, y: y};
    while (v != null) {
        tmpPath.push(v);
        v = getTileNextMove(v.i, v.x, v.y);
    }
    selectedPath = tmpPath;
}

function getTileNextMove(i, x, y)
{
    var s = tilesSurroundingTile(x, y);
    var value = tileMap[i].movemap[x*mapSizes + y];
    for (var j=0; j<s.length; j++) {
        var w = wrapMapVect(i, s[j].x, s[j].y);
        if (!w) continue;
        if (tileMap[w.i].movemap[w.x*mapSizes + w.y] > value)
            return w;
    }
    return null;
}

function wrapMapVect(i, x, y)
{
    if (x < 0) {
        i -= 1;
        x += mapSizes;
    } else if (x >= mapSizes) {
        i += 1;
        x -= mapSizes;
    }
    if (y < 0) {
        i -= 2;
        y += mapSizes;
    } else if (y >= mapSizes) {
        i += 2;
        y -= mapSizes;
    }
    if (i < 0 || i > 3 || !tileMap[i].valid)
        return null;
    return {i: i, x: x, y: y};
}

/* Action select mode. */
function ActionModeInit(i, x, y)
{
    if (!nation) return;

    /* Find surrounding enemies. */
    var attack = new Array();
    var tiles = tilesSurroundingTile(x, y);
    for (var j=0; j<tiles.length; j++) {
        var vt = vectToWorldVect(i, tiles[j]);
        var b = getBuildableAt(vt.i, vt.x, vt.y, 'm');
        if (b && b.n && b.n != nation.name && isBuildableVisable(vt.i, b)) {
            attack.push(getPosFromi(vt.i, vt.x, vt.y));
        }
    }

    /* Set highlighter. */
    if (attack.length > 0) {
        globalSelectFunct = TileListHighlighter(attack);
        var bpos = getWorldPos(i);
        ActionModeStart = {bx: bpos.x, by: bpos.y, x: x, y: y};
    } else {
        globalSelectFunct = null;
        ActionModeStart = null;
    }
}

/* Action Mode data. */
ActionModeData = new Array();
ActionModeStart = null;
SmokeData = new Array();

/* Perform action mode. */
function ActionModeDo(aBlockPos, dBlockPos, buildId)
{
    /* End mode. */
    globalSelectFunct = null;
    render();

    /* Perform later if the movement has not happened yet. */
    var ai = getiFromWorldPos(aBlockPos.bx, aBlockPos.by);
    if (ai < 0) return;
    var b = getBuildableAt(ai, aBlockPos.x, aBlockPos.y, 'm');
    if (!b || b.id != buildId) {
        ActionModeData.push({a: aBlockPos, d: dBlockPos, id: buildId});
        return;
    }

    /* Attack. */
    RequestJSON("POST", "/set/attack", {dbx: dBlockPos.bx, dby: dBlockPos.by,
                                        dx: dBlockPos.x, dy: dBlockPos.y,
                                        abx: aBlockPos.bx, aby: aBlockPos.by,
                                        ax: aBlockPos.x, ay: aBlockPos.y});
    AddSmoke(aBlockPos, dBlockPos);
}

/* Add attacking smoke image. */
function AddSmoke(aBlockPos, dBlockPos)
{
    SmokeData.push({a: aBlockPos, d: dBlockPos});
}

/* Draw smoke. */
function DrawSmoke()
{
    for (var i=0; i<SmokeData.length; i++) {
        var data = SmokeData[i];
        var i1 = getiFromWorldPos(data.a.bx, data.a.by);
        var i2 = getiFromWorldPos(data.d.bx, data.d.by);
        if (i1 < 0 || i2 < 0) continue;
        var pos1 = getScreenCoordFromPos(getPosFromi(i1, data.a.x, data.a.y));
        var pos2 = getScreenCoordFromPos(getPosFromi(i2, data.d.x, data.d.y));

        var d = Vect(Math.floor((pos1.x + pos2.x - ImgSmoke.width) / 2),
                     Math.floor((pos1.y + pos2.y - ImgSmoke.height) / 2));

        var xdist = pos2.x - pos1.x;
        var ydist = pos2.y - pos1.y;
        var d1 = Vect(Math.floor(pos1.x + xdist*0.2 - ImgFire.width/2),
                      Math.floor(pos1.y + ydist*0.2 - ImgFire.height/2));
        var d2 = Vect(Math.floor(pos1.x + xdist*0.8 - ImgFire.width/2),
                      Math.floor(pos1.y + ydist*0.8 - ImgFire.height/2));

        ctx.drawImage(ImgFire, d1.x, d1.y, ImgFire.width, ImgFire.height);
        ctx.drawImage(ImgFire, d2.x, d2.y, ImgFire.width, ImgFire.height);
        ctx.drawImage(ImgSmoke, d.x, d.y, ImgSmoke.width, ImgSmoke.height);
    }
}
