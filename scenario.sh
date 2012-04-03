#!/bin/bash

for flags in "" "--enable"; do
	python tests/scenario.py --dir exptdata/tcpvsudp -t 120 -n 4 --run tcpvsudp $flags
	python tests/scenario.py --dir exptdata/tcp2vs32 -t 120 --run tcp2vs32 $flags
done
