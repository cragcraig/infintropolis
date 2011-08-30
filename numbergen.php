<html>
<head>
<style type="text/css">
	canvas { border: 1px solid black; }
	@font-face {
		font-family: "catan";
		src: url("img/shrewsbury.woff") format("woff"),
		url("img/shrewsbury.ttf") format("truetype");
	}
</style>
<script type="text/javascript">

var canvas;

function drawit()
{
	canvas = document.getElementById('canvas');
	var ctx = canvas.getContext("2d");

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

	ctx.textAlign = "center";
	ctx.textBaseline = "middle";
	ctx.font = "12pt catan";
	ctx.fillStyle = "#ffff26";
	ctx.strokeStyle = "#ff3000";
	ctx.lineWidth = 1;
	ctx.shadowColor = "rgba(255,102,0,1)";
	ctx.shadowBlur = 4;
	
	var dx = canvas.width/2;
	var dy = canvas.height/2;
	
	for (var i=0; i < 6; i++) {
		ctx.strokeText((i+1),dx+23/32*TileVerts[i].x,dy+23/32*TileVerts[i].y);
		ctx.fillText((i+1),dx+23/32*TileVerts[i].x,dy+23/32*TileVerts[i].y);
	}
	ctx.shadowColor = "rgba(0,0,0,0)";
}
</script>
</head>

<body onload="drawit()">
<canvas width="188" height="158" id="canvas">
Canvas unsupported by browser.
</canvas>
</body>
<br>
<br>
<a href="javascript: alert('Browser error, sorry');" onClick="this.href=canvas.toDataURL()" target="_b    lank">Screenshot</a> | 
<a href="javascript: drawit();">Redraw</a>
</html>
