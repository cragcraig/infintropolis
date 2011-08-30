<?php
/* defines */
define("BLOCK_SIZE", "50");

$prob = array(
	array(5, 50, 30, 10, 30, 80, 90),
	array(0, 0, 65, 75, 85, 95, 100),
	array(0, 20, 0, 0, 0, 0, 100)
);

/* generate map filename */
function mapname($x, $y)
{
	return 'map/' . $x . '_' . $y . '.map';
}

/* save map */
function writemap($fname, &$m)
{
	$str = '';

	for ($i=0; $i < BLOCK_SIZE; $i++) {
		for ($j=0; $j < BLOCK_SIZE; $j++) {
			$str .= $m[$i][$j][0] . ':' . $m[$i][$j][1] . ',';
		}
	}
	file_put_contents($fname, $str, LOCK_EX);

	echo $str;

	return true;
}

/* load map from file */
function loadmap($fname, &$map)
{
	if (!file_exists($fname)) {
		$map = null;
		return;
	}

	/* load file */
	$mfile = file_get_contents($fname);
	$a = explode(',', $mfile);

	$k = 0;
	for ($i=0; $i < BLOCK_SIZE; $i++) {
		for ($j=0; $j < BLOCK_SIZE; $j++) {
			$b = explode(':', $a[$k]);
			$k++;
			$map[$i][$j][0] = $b[0];
			$map[$i][$j][1] = $b[1];
		}
	}
}

/* random dice token */
function randroll($tiletype)
{
	if ($tiletype == 1 || $tiletype == 7) return 0;
	else return ((rand(0,99) < 50) ? rand(2,6) : rand(8,12));
}

/* find neighbor tile coordinates */
function getneighbor($x, $y, $dir, &$xout, &$yout)
{
	$xout = $x;
	$yout = $y;

	if ($dir == 1)
		$yout -= 1;
	elseif ($dir == 4)
		$yout += 1;
	else {
		if ($dir == 0 || $dir == 5)
			$xout += 1;
		elseif ($dir == 2 || $dir == 3)
			$xout -= 1;

		if (!($x % 2) && ($dir == 0 || $dir == 2))
			$yout -= 1;
		elseif ($x % 2 && ($dir == 3 || $dir == 5))
			$yout += 1;
	}
}

function sumland($x, $y, &$map, &$smap)
{
	$sum = 0;

	$tx = 0;
	$ty = 0;

	for ($i=0; $i < 6; $i++) {
		getneighbor($x, $y, $i, $tx, $ty);
		if ($tx < BLOCK_SIZE && $tx >= 0 && $ty < BLOCK_SIZE && $ty >= 0)
			$t = $map[$tx][$ty][0];
		elseif ($tx < 0 && $ty >= 0 && $ty < BLOCK_SIZE)
			$t = $smap[2][$tx+BLOCK_SIZE][$ty][0];
		elseif ($tx >= BLOCK_SIZE && $ty >= 0 && $ty < BLOCK_SIZE)
			$t = $smap[0][$tx-BLOCK_SIZE][$ty][0];
		elseif ($ty < 0 && $tx >= 0 && $tx < BLOCK_SIZE)
			$t = $smap[1][$tx][$ty+BLOCK_SIZE][0];
		elseif ($ty >= BLOCK_SIZE && $tx >= 0 && $tx < BLOCK_SIZE)
			$t = $smap[3][$tx][$ty-BLOCK_SIZE][0];
		else
			$t = 0;
			
		if ($t > 1) $sum++;
	}

	return $sum;
}


function gentile($x, $y, &$map, &$smap, &$probarray) {
	$sum = sumland($x, $y, $map, $smap);

	/* land tile */
	if (rand(1,100) < $probarray[$sum]) {
		
		/* resource type */
		$tt = rand(2, 7);
		if ($tt == 7) {
			$tt = rand(1,20);
			if ($tt == 1) $tt = 8;
			elseif ($tt <= 4) $tt = 9;
			elseif ($tt <= 12) $tt = 7;
			else $tt = rand(2, 6);
		}

		$map[$x][$y][0] = $tt;
	}

	/* roll token */
	$map[$x][$y][1] = randroll($map[$x][$y][0]);
	
}

/**** ALGORITHM ****/

/* generate filename */
$x = intval($_GET['x']);
$y = intval($_GET['y']);

/* ensure map doesn't exist */
if (!file_exists(mapname($x,$y))) {

	/* variables */
	$map = array();

	/* check nearby maps */
	$smap = array();
	loadmap(mapname($x+1,$y+0), $smap[0]);
	loadmap(mapname($x+0,$y-1), $smap[1]);
	loadmap(mapname($x-1,$y+0), $smap[2]);
	loadmap(mapname($x+0,$y+1), $smap[3]);

	/* clear map */
	for ($i=0; $i < BLOCK_SIZE; $i++) {
		for ($j=0; $j < BLOCK_SIZE; $j++) {
			$map[$i][$j][0] = 1;
			$map[$i][$j][1] = 0;
		}
	}

	/* generate in multiple spiral passes */
	for ($t=0; $t < count($prob); $t++) {
		for ($i=BLOCK_SIZE-1, $j=0; $i >= 0; $i--, $j++) {
			for ($k=$j; $k < $i; $k++)
				gentile($j, $k, $map, $smap, $prob[$t]);
			for ($k=$j; $k < $i; $k++)
				gentile($k, $i, $map, $smap, $prob[$t]);
			for ($k=$i; $k > $j; $k--)
				gentile($i, $k, $map, $smap, $prob[$t]);
			for ($k=$i; $k > $j; $k--)
				gentile($k, $j, $map, $smap, $prob[$t]);
		}
	}

	/* write map */
	writemap(mapname($x, $y), $map);
} else {
	echo file_get_contents(mapname($x, $y));
}

?>
