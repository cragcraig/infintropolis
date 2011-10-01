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
var screenX = 24;
var screenY = 24;
var screenOffsetX = 0;
var screenOffsetY = 0;
var screenWidth;
var screenHeight;

// state
var globalState = 0;
var globalBuildState = false;
var selectedTile;
var selectedVertex;
var selectedEdge;
var tDrawRollTokens = true;

// map
var mapX = Infinity;
var mapY = Infinity;
var mapSizes = 50;
var tileMap = [];
var tileLoader = [];
var civLoader = [];

/* MapBlock object constructor */
function MapBlock()
{
	var o = {valid: false, map: new Array(mapSizes), buildables: new Array()};
	
	for (var j=0; j < mapSizes; j++) {
		o.map[j] = new Array(mapSizes);
	}

	return o;
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

function JSONCallback(json)
{
    /* json error */
    var error = false;
    if (json.error) {
        error = true;
    } else {

        /* parse block data */
        for (i=0; i<tileMap.length; i++) {
            var pos = getWorldPos(i);
            var id = pos.x + '_' + pos.y;
            if (json[id]) {
                /* map data */
                if (json[id].mapblock) {
                    error = parseMapBlock(i, json[id].mapblock);
                    tileMap[i].valid = true;
                }
                /* buildable data */
                if (json[id].buildableblock) {
                    error = parseBuildableBlock(i, json[id].buildableblock);
                }
            }
        }

        /* parse capitol and nation data */
    }
    render();
}

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

function parseBuildableBlock(i, list)
{
    tileMap[i].buildables = list;
}

function requestMap(i)
{
	if (mapX == Infinity || mapY == Infinity ||
        mapX == NaN || mapY == NaN) return;

	/* map id */
	var x = mapX + (i == 0 || i == 2 ? 0 : 1);
	var y = mapY + (i == 0 || i == 1 ? 0 : 1);
	tileMap[i].valid = false;

	/* XHR */
    RequestJSON("/get/map?bx="+x+"&by="+y, JSONCallback);
}

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
	
	/* request */
	for (var i=0; i < 4; i++) {
		if (!tileMap[i].valid) {
			/* get map file */
			requestMap(i);
		}
	}

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
	if (x < 0 || y < 0 || x >= mapSizes || y >= mapSizes || !tileMap[i].valid) {
		return {type: 0, roll: 0};
	}
	return tileMap[i].map[x][y];

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
	if (mouseScrollTimer != null) return;

    /* UI click */
    if (UIHandleClick(pureMouseX, pureMouseY))
        return;

    /* build click */
    if (globalBuildState) {
        BuildModeDo();
        return;
    }

    /* start mouse scroll */
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

// load tiles
var numTilesImgs = 10;
var tiles = [];
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
	for (i=0; i<numTilesImgs; i++) {
		tiles[i] = loadImg('/img/' + i + '.png');
	}
	highlightedTile = loadImg('/img/high.png');
	// load tokens
	for (i=0; i<11; i++) {
		tokens[i] = loadImg('/img/tokens/' + (i+2) + '.png');
	}
	for (i=0; i<1; i++) {
		specialTokens[i] = loadImg('/img/tokens/s' + i + '.png');
	}
    // create UI buttons
    UIAddButton(UIButton(-60, 50, loadImg('/img/buttons/settlement.png'), 0,
                         function () {BuildModeEnable('s');}));
    UIAddButton(UIButton(-60, 110, loadImg('/img/buttons/road.png'), 0,
                         function () {BuildModeEnable('r');}));
    UIAddButton(UIButton(-60, 50, loadImg('/img/buttons/cancel.png'), 1,
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

	// set map position
	goMap(0, 0);

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
        drawLoadingMapText();
}

// Check if pending map requests.
function isAllMapsLoaded()
{
    r = true;
    for (i = 0; i < 4; i++) {
        if (!tileMap[i].valid)
            r = false;
    }
    return r;
}

// Draw "Map Loading" text.
function drawLoadingMapText()
{
	ctx.font = "18pt serif";
	ctx.fillStyle = "#fff";
	ctx.strokeStyle = "#000";
    ctx.lineWidth = 2;
	ctx.textAlign = "center";
	ctx.textBaseline = "top";
	ctx.strokeText("[ loading map data ]", canvas.width/2, 10);
	ctx.fillText("[ loading map data ]", canvas.width/2, 10);
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
	ctx.lineWidth = 3.0;
	ctx.beginPath();
	ctx.moveTo(px+10, py+10);
	ctx.lineTo(px-10, py+10);
	ctx.lineTo(px-10, py-5);
	ctx.lineTo(px, py-13);
	ctx.lineTo(px+10, py-5);
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

	var dx1, dx2, dy1, dy2;
	
	switch (e.d) {
		case 't':
			dx1 = px + (TileVerts[3].x - TileVerts[4].x)/5 + TileVerts[4].x;
			dx2 = px + (TileVerts[3].x - TileVerts[4].x)*4/5 + TileVerts[4].x;
			dy1 = py + (TileVerts[3].y - TileVerts[4].y)/5 + TileVerts[4].y;
			dy2 = py + (TileVerts[3].y - TileVerts[4].y)*4/5 + TileVerts[4].y;
		break;

		case 'c':
			dx1 = px - TileWidth/2;
			dy1 = py - (TileEdge*3/5)/2;
			dx2 = px - TileWidth/2;
			dy2 = py + (TileEdge*3/5)/2;
		break
		
		case 'b':
			dx1 = px + (TileVerts[5].x - TileVerts[0].x)/5 + TileVerts[0].x;
			dx2 = px + (TileVerts[5].x - TileVerts[0].x)*4/5 + TileVerts[0].x;
			dy1 = py + (TileVerts[5].y - TileVerts[0].y)/5 + TileVerts[0].y;
			dy2 = py + (TileVerts[5].y - TileVerts[0].y)*4/5 + TileVerts[0].y;
		break;
	}

	// draw
	ctx.beginPath();
    if (e.alpha)
        ctx.globalAlpha = e.alpha;
	ctx.lineCap = "round";
	ctx.moveTo(dx1, dy1);
	ctx.lineTo(dx2, dy2);
	ctx.closePath();
	ctx.strokeStyle = "#" + e.c1;
	ctx.lineWidth = 8.0;
	ctx.stroke();
	ctx.strokeStyle = "#" + e.c2;
	ctx.lineWidth = 4.0;
	ctx.stroke();
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
	ctx.drawImage(tiles[tile.type], dx - TileWidth/2, dy - TileHeight/2);

	if (tDrawRollTokens && tile.roll != 0) {
		/* circle */
		var color = (tile.roll == 6 || tile.roll == 8) ? "#ad151b" : "#000";
		var numDots = tile.roll - 2;
		ctx.drawImage(tokens[numDots], dx - tokens[numDots].width/2, dy - tokens[numDots].height/2);
	}
	/* event text */
	if (tDrawRollTokens && tile.type == 9) {
		ctx.drawImage(specialTokens[0], dx - specialTokens[0].width/2, dy - specialTokens[0].height/2);
	}
		
}

// Draw a buildable
function drawBuildable(buildable)
{
    if (buildable == undefined) return;

    // Check visibility.
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
	
	var v = {x : 0, y : 0, d : 't', alpha: 0.65, c1: "000", c2: "fff"};
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
	
	var v = {x : 0, y : 0, d : 't', alpha: 0.65, c1: "000", c2: "fff"};
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
function RequestJSON(url, callback)
{
    req = new XMLHttpRequest();
    req.onreadystatechange = genRequestCallback(req, callback);
	req.open("GET", url, true);
	req.setRequestHeader("Cache-Control", "no-cache");
	req.setRequestHeader("Pragma", "no-cache");
	req.send(null);
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
            if (req.status == 200) {
                callback(JSON.parse(req.responseText));
            } else {
                callback({error: true});
            }
            delete req;
        }
    };
}

/* The user interface data.
 *
 * UIButtons: Holds the list of UI buttons.
 * UIMapType: Maps buildable types {vertex/edge} => {true/false}.
 */
UIButtons = new Array();
UIMapType = {s: true, c: true, r: false, b: false};

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
    globalState = (UIMapType[buildType] ? 2 : 3);
    globalBuildState = buildType;
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
        selected.x = (selected.x + screenX) % mapSizes;
        selected.y = (selected.y + screenY) % mapSizes;
        i = getiFromPos(selected.x, selected.y);
        selected.t = globalBuildState;
        selected.i = i;
        tileMap[i].buildables.push(selected);
        var block = getWorldPos(i);
        /* Launch build request. */
        RequestJSON("/set/build?bx="+block.x+"&by="+block.y+
                    "&x="+selected.x+"&y="+selected.y+
                    "&d="+selected.d+"&type="+selected.t+
                    "&capitol=0", JSONCallback);
    }
    BuildModeCancel();
}
