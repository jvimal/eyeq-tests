#!/bin/bash

exptid=`date +%b%d-%H:%M`
dir=/tmp/$exptid/timescale
time=120

ctrlc() {
	killall -9 python
	exit
}

trap ctrlc SIGINT

for run in {1..10}; do
for iso in "" "--enable"; do
for wtcp in 4; do
	subdir=$dir/$run-$iso-wtcp$wtcp
	python tests/scenario.py --run tcpvsudp -n 2 --dir $subdir \
		--exptid $dir --time 100 \
		--traffic ~/vimal/exports/loadfiles/tmp2 $iso \
		--wtcp $wtcp
done
done
done

echo `date` $dir
