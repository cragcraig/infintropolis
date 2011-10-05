#!/bin/sh

convert '(' tiles/{0,1,2,3,4,5,6,7,8,9,10}.png +append ')' -background none -append tiles.png
