#!/bin/sh

convert '(' tiles/{0,1,2,3,4,5,6,7,8,9,10}.png +append ')'\
        '(' tiles/{0,1,2,3,4,5,6,7,8,9,10}.png +append -modulate 40 ')'\
        -background none -append tiles.png
