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
var globalState = 0;
var globalBuildState = false;
var globalDebug = false;
var selectedTile;
var selectedVertex;
var selectedEdge;
var tDrawRollTokens = true;

// nation
var capitol = null;

// map
var mapX = 0;
var mapY = 0;
var mapSizes = 50;
var tileMap = [];
var tileLoader = [];
var civLoader = [];

/* MapBlock object constructor. */
function MapBlock()
{
    var o = {valid: false, invalidLOS: false, token: 0,
             map: new Array(mapSizes), buildables: new Array()};
    
    for (var j=0; j < mapSizes; j++) {
        o.map[j] = new Array(mapSizes);
    }

    return o;
}

/* Vect object constructor. */
function Vect(x, y)
{
    return {"x": x, "y": y};
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

function getiFromPos(x, y)
{
    return (x < mapSizes ? 0 : 1) + (y < mapSizes ? 0 : 2);
}

function getPosFromi(i, x, y)
{
    return Vect(x + (i == 0 || i == 2 ? 0 : mapSizes),
                y + (i == 0 || i == 1 ? 0 : mapSizes));
}

/* Parses a JSON response from the server.
 *
 * json: A decoded object from the server.
 */
function JSONCallback(json)
{
    /* json error */
    var error = false;
    if (json.error) {
        error = true;
    } else {
        /* parse capitol and nation data */
        if (json['capitol']) {
            parseCapitol(json['capitol']);
        }

        /* parse block data */
        for (i=0; i<tileMap.length; i++) {
            var pos = getWorldPos(i);
            var id = pos.x + '_' + pos.y;
            if (json[id]) {
                /* block token */
                if (json[id].token) {
                    tileMap[i].token = json[id].token;
                }
                /* buildable data */
                if (json[id].buildableblock) {
                    error = parseBuildableBlock(i, json[id].buildableblock);
                }
                /* map data */
                if (json[id].mapblock) {
                    error = parseMapBlock(i, json[id].mapblock);
                    tileMap[i].valid = true;
                    tileMap[i].invalidLOS = false;
                }
            }
        }

        /* Update LOS on an as-needed basis. */
        updateLOSAsNeeded();
    }
    render();
}

/* Parses a Capitol JSON object. */
function parseCapitol(json)
{
    if (!json.nation) return;
    if (!capitol || (json.number != capitol.number)) {
        var xoff = 0;
        var yoff = 0;
        if (json.x < mapSizes/2) xoff = 1;
        if (json.y < mapSizes/2) yoff = 1;
        goMap(json.bx - xoff, json.by - yoff);
        screenX = json.x - Math.round(screenWidth/2) + mapSizes*xoff;
        screenY = Math.floor((json.y - Math.floor(screenHeight/2))/2)*2
                  + mapSizes*yoff;
    }
    capitol = json;
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
    var count = -1;
    if (tileMap[i].buildables.length > 0) {
        count = countBuildables(i);
    }

    /* Use new data and start autoupdate. */
    tileMap[i].buildables = list;
    launchAutoUpdate();

    /* Re-count buildables and issue LOS update if needed. */
    if (count != -1) {
        if (count != countBuildables(i)) {
            tileMap[i].invalidLOS = true;
        }
    }
}

/* Counts the number of buildables owned by the nation in tileMap[i].
 *
 * TODO(craig): This method will have to change once volcanoes and knights are
 * implemented as they can change the LOS without changing the buildables count.
 * */
function countBuildables(i)
{
    if (!capitol || !tileMap[i].valid) {
        return 0;
    }
    var count = 0;
    for (var j=0; j < tileMap[i].buildables.length; j++) {
        if (tileMap[i].buildables[j].n == capitol.nation) {
            count++;
        }
    }
    return count;
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

    /* set position */
    mapX = worldX;
    mapY = worldY;
    
    /* request blocks */
    var req = new Array();
    for (var i=0; i < 4; i++) {
        if (!tileMap[i].valid) {
            req.push(i);
        }
    }
    requestBlocks(req, true);
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
    
    canvas.touchstart = mouseTouch;
    canvas.touchend = mouseOutCallback;
    canvas.touchmove = updateMouse;
}

/* callbacks */
function mouseCallback()
{
    reportUserActivity();

    /* UI click */
    if (UIHandleClick(pureMouseX, pureMouseY))
        return;

    /* build click */
    if (globalBuildState) {
        BuildModeDo();
        return;
    }

    /* start mouse scroll */
    if (mouseScrollTimer != null) return;
    mouseScrollTimer = setInterval(mouseScroll, dragDelay);

    oldMouseX = pureMouseX;
    oldMouseY = pureMouseY;

    canvas.style.cursor = 'move';
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
var highlightedTile;
var tokens = [];
var specialTokens = [];

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
    
    ctx.font = "50pt serif";
    ctx.fillStyle = "#fff";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("Infintropolis", canvas.width/2, canvas.height/2 - 50);
    ctx.fillText("is loading...", canvas.width/2, canvas.height/2 + 50);

    // init map
    initMap();

    // load tiles
    tileSprite = loadImg('/img/tiles.png');
    highlightedTile = loadImg('/img/high.png');
    // load tokens
    for (i=0; i<11; i++) {
        tokens[i] = loadImg('/img/tokens/' + (i+2) + '.png');
    }
    for (i=0; i<1; i++) {
        specialTokens[i] = loadImg('/img/tokens/s' + i + '.png');
    }
    // create UI buttons
    UIAddButton(UIButton(-60, 50, loadImg('/img/ui/settlement.png'), 0,
                         function () {BuildModeEnable('s');}));
    UIAddButton(UIButton(-60, 110, loadImg('/img/ui/settlement.png'), 0,
                         function () {BuildModeEnable('c');}));
    UIAddButton(UIButton(-60, 170, loadImg('/img/ui/road.png'), 0,
                         function () {BuildModeEnable('r');}));
    UIAddButton(UIButton(-60, 230, loadImg('/img/ui/road.png'), 0,
                         function () {BuildModeEnable('b');}));
    UIAddButton(UIButton(-60, 50, loadImg('/img/ui/cancel.png'), 1,
                         BuildModeCancel));
    UIGroupVisible(0, true);

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

    // request server data
    RequestJSON("GET", "/get/capitol", {'capitol': 0});

    // keypress
    document.onkeydown = keyPressCallback;
    document.onkeyup = keyReleaseCallback;

    // mouse scroll
    initMouseScroll();

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

    UIRenderButtons();

    if (!isAllMapsLoaded())
        drawLoadingMapText("loading map");
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
    return r == tileMap.length;
}

// Draw "Map Loading" text.
function drawLoadingMapText(str)
{
    ctx.font = "18pt serif";
    ctx.fillStyle = "#fff";
    ctx.strokeStyle = "#000";
    ctx.lineWidth = 2;
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    ctx.strokeText("[ " + str + " ]", canvas.width/2, 10);
    ctx.fillText("[ " + str + " ]", canvas.width/2, 10);
}

// render highlight tile
function drawHighlightTile(x, y)
{
    ctx.drawImage(highlightedTile, outputx(x,y) - TileWidth/2, outputy(x,y) - TileHeight/2);
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

    // draw
    if (v.alpha)
        ctx.globalAlpha = v.alpha;
    ctx.fillStyle = "#" + v.c2;
    ctx.strokeStyle = "#" + v.c1;
    ctx.lineWidth = 3.5;
    ctx.beginPath();
    if (v.t == 's') {
        ctx.moveTo(px+8, py+8);
        ctx.lineTo(px-8, py+8);
        ctx.lineTo(px-8, py-4);
        ctx.lineTo(px, py-11);
        ctx.lineTo(px+8, py-4);
    } else {
        ctx.moveTo(px+13, py+8);
        ctx.lineTo(px-12, py+8);
        ctx.lineTo(px-12, py-9);
        ctx.lineTo(px-5, py-15);
        ctx.lineTo(px+2, py-9);
        ctx.lineTo(px+2, py-5);
        ctx.lineTo(px+13, py-5);
    }
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
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
        ctx.lineWidth = 10.0;
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
        ctx.lineWidth = 3.5;
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
    for (i=-1; i<screenWidth+2; i++) {
        for (j=-2; j<screenHeight+2; j++) {
            drawTile(getTile(i+screenX, j+screenY), i, j);
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
            drawBuildable(drawable);
        }
    }
}

// Draw a tile
function drawTile(tile, x, y)
{
    if (tile == undefined) return;

    var dx = outputx(x,y);
    var dy = outputy(x,y);
    ctx.drawImage(tileSprite, TileWidth * tile.type,
                  (tile.roll == -1 ? TileHeight : 0), TileWidth, TileHeight,
                  dx - TileWidth/2, dy - TileHeight/2, TileWidth, TileHeight);

    if (tDrawRollTokens && tile.roll > 0) {
        /* circle */
        var color = (tile.roll == 6 || tile.roll == 8) ? "#ad151b" : "#000";
        var numDots = tile.roll - 2;
        ctx.drawImage(tokens[numDots], dx - tokens[numDots].width/2, dy - tokens[numDots].height/2);
    }
    /* event text */
    if (tDrawRollTokens && tile.type == 9 && tile.roll != -1) {
        ctx.drawImage(specialTokens[0], dx - specialTokens[0].width/2, dy - specialTokens[0].height/2);
    }
    /* draw debug text */
    if (globalDebug) {
        ctx.font = "16pt serif";
        ctx.fillStyle = "#000";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText((x + screenX)%mapSizes + "," + (y + screenY)%mapSizes, dx, dy);
    }
}

// Draw a buildable
function drawBuildable(buildable)
{
    if (buildable == undefined || buildable.x < -1 || buildable.y < -2 ||
        buildable.x > screenWidth + 2 || buildable.y > screenWidth + 2) return;

    // Check buildable type.
    if (buildable.t == 'r' || buildable.t == 'b') {
        drawEdge(buildable)
    } else {
        drawVertex(buildable)
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
            if (req.status == 200 && req.responseText != '') {
                res = JSON.parse(req.responseText);
                if (res.logout) {
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
    RequestJSON("GET", url, blockList);
}

/* The user interface data.
 *
 * UIButtons: Holds the list of UI buttons.
 * BuildablesTypeMap: Maps buildable types {vertex/edge} => {true/false}.
 */
UIButtons = new Array();
UIBuildablesTypeMap = {s: true, c: true, r: false, b: false};

/* A user interface button.
 *
 * x: Screen position. Negative values are relative to the right edge.
 * y: Screen position. Negative values are relative to the bottom edge.
 */
function UIButton(x, y, img, group, callback)
{
    var o = {x: x, y: y, img: img, callback: callback, group: group,
             enabled: false}

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
    for (i=0; i<UIButtons.length; i++) {
        if (!UIButtons[i].enabled) continue;
        x = UIButtons[i].x + (UIButtons[i].x < 0 ? canvas.width : 0);
        y = UIButtons[i].y + (UIButtons[i].y < 0 ? canvas.height : 0);
        if (clickx > x && clickx < x + UIButtons[i].img.width &&
            clicky > y && clicky < y + UIButtons[i].img.height) {
            UIButtons[i].callback();
            return true;
        }
    }
    return false;
}

/* Renders visible UIButton objects to the canvas. */
function UIRenderButtons()
{
    var x;
    var y;
    for (i=0; i<UIButtons.length; i++) {
        if (!UIButtons[i].enabled) continue;
        x = UIButtons[i].x + (UIButtons[i].x < 0 ? canvas.width : 0);
        y = UIButtons[i].y + (UIButtons[i].y < 0 ? canvas.height : 0);
        ctx.drawImage(UIButtons[i].img, x, y);
    }
}

/* Enable Build Mode.
 *
 * buildType: {s, c, r, b}
 */
function BuildModeEnable(buildType)
{
    globalState = (UIBuildablesTypeMap[buildType] ? 2 : 3);
    globalBuildState = buildType;
    selectedVertex = null
    selectedEdge = null
    UIGroupVisible(0, false);
    UIGroupVisible(1, true);
    render();
}

/* End Build Mode. */
function BuildModeCancel()
{
    globalState = 0;
    selectedTile = null;
    selectedVertex = null;
    selectedEdge = null;
    globalBuildState = false;
    UIGroupVisible(0, true);
    UIGroupVisible(1, false);
    render();
}

/* Build a buildable at the currently selected location. */
function BuildModeDo()
{
    if (!globalBuildState) return;
    var selected = (globalState == 2 ? selectedVertex : selectedEdge);
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
                    d: selected.d, type: selected.t, capitol: 0});
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

/* Checks if the buildable is adjacent to a visable tile.
 *
 * Returns true if an adjacent tile is visible, false otherwise.
 */
function isBuildableVisable(i, bld)
{
    st = tilesSurroundingBuildable((bld.t == 'r' || bld.t == 'b'),
                                   bld.x, bld.y, bld.d);
    for (var j=0; j<st.length; j++) {
        v = getPosFromi(i, st[j].x, st[j].y);
        t = getTile(v.x, v.y);
        if (t.roll != -1)
            return true;
    }
    return false;
}

/* Loading Animation. */
loadingAnimation = {"t1": 0, "t2": 0, "enabled": false, "lastX": 0, "lastY": 0,
                    "hue": 0};
function loadingAnimationStart()
{
    if (loadingAnimation.enabled == false) {
        ctx.fillStyle = 'rgba(0,0,0,1)';
        ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
        loadingAnimation.lastX = loadingAnimationRandomX();
        loadingAnimation.lastY = loadingAnimationRandomY();
        loadingAnimation.hue = Math.random() * 255;
        loadingAnimation.t1 = setInterval(loadingAnimationDraw, 50);
        loadingAnimation.t2 = setInterval(loadingAnimationFade, 40);
        loadingAnimation.enabled = true;
    }
}

function loadingAnimationStop()
{
    if (loadingAnimation.enabled == true) {
        clearInterval(loadingAnimation.t1);
        clearInterval(loadingAnimation.t2);
        loadingAnimation.enabled = false;
    }
}

function loadingAnimationDraw()
{
    ctx.save();
    ctx.translate(ctx.canvas.width/2, ctx.canvas.height/2);
    ctx.scale(0.9, 0.9);
    ctx.translate(-ctx.canvas.width/2, -ctx.canvas.height/2);
    ctx.beginPath();
    ctx.lineWidth = 5 + Math.random() * 10;
    ctx.moveTo(loadingAnimation.lastX, loadingAnimation.lastY);
    loadingAnimation.lastX = loadingAnimationRandomX();
    loadingAnimation.lastY = loadingAnimationRandomY();
    ctx.bezierCurveTo(loadingAnimationRandomX(),
                      loadingAnimationRandomY(),
                      loadingAnimationRandomX(),
                      loadingAnimationRandomY(),
                      loadingAnimation.lastX, loadingAnimation.lastY);

    loadingAnimation.hue = loadingAnimation.hue + 10 * Math.random();
    ctx.strokeStyle = 'hsl(' + loadingAnimation.hue + ', 50%, 50%)';
    //ctx.strokeStyle = 'rgba(200, 0, 0, 1.0)';
    ctx.shadowColor = 'white';
    ctx.shadowBlur = 15;
    ctx.stroke();
    ctx.restore();
}

function loadingAnimationFade()
{
    ctx.fillStyle = 'rgba(0,0,0,0.1)';
    ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
    drawLoadingMapText("loading world");
}

function loadingAnimationRandomX()
{
    return ctx.canvas.width/2 * Math.random() + ctx.canvas.width/4;
}

function loadingAnimationRandomY()
{
    return ctx.canvas.height/2 * Math.random() + ctx.canvas.height/4;
}
