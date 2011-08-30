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
	var roll = <?php echo $_GET['roll'] ?>;
	canvas = document.getElementById('canvas');
	var ctx = canvas.getContext("2d");
	var color = (roll == 6 || roll == 8) ? "#ad151b" : "#000";
	var dx = 21;
	var dy = 21;

	ctx.fillStyle = "#cabea5";
	ctx.strokeStyle = "#000";
	ctx.lineWidth = 2;
	ctx.beginPath();
	ctx.arc(dx, dy, 20, 0, 2*Math.PI, true);
	ctx.closePath();
	ctx.fill();
	ctx.stroke();
		
	/* text */
	ctx.textAlign = "center";
	ctx.textBaseline = "middle";
	ctx.font = "16pt catan";
	ctx.fillStyle = color;
	ctx.fillText(((roll == 7) ? '?' : roll),dx,dy-1);

	var numDots = (roll < 7) ? roll - 1 : 13 - roll;
	ctx.fillStyle = color;

	if (roll != 7) {
		for (var i=0; i < numDots; i++) {
			ctx.beginPath();
			ctx.arc(dx + (-(numDots-1)/2+i)*5, dy + 10, 2, 0, 2*Math.PI, true);
			ctx.closePath();
			ctx.fill();
		}
	}
}
</script>
</head>

<body onload="drawit()">
<canvas width="42" height="42" id="canvas">
Canvas unsupported by browser.
</canvas>
</body>

<a href="javascript: alert('Browser error, sorry')" onClick="this.href=canvas.toDataURL()" target="_b    lank">Screenshot</a>
</html>
