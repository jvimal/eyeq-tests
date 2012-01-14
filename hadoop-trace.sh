#!/bin/bash

exptid=`date +%b%d-%H:%M`
time=120
start=`date`

ctrlc() {
	killall -9 python
	exit
}

trap ctrlc SIGINT

echo exptid $exptid

python tests/genconfig.py --type udp -n 16 --tenant 2 \
	--traffic fullmesh -P 1 --size 1G \
	--port 12347 \
	--time 86400 --inter 30 > ~/vimal/exports/loadfiles/hadoop-trace-cross-10G

for mtu in 9000; do
for size in 1T 10T 100T; do
for iso in "" "--enable"; do
	subdir=size$size-iso$iso-mtu$mtu
	python tests/test_hadoop_trace.py --mtu 9000 \
		--dir /tmp/$exptid/$subdir --size $size \
		--traffic ~/vimal/exports/loadfiles/hadoop-trace-cross-10G \
		--exptid $exptid $iso
done
done
done

echo $start $exptid
echo `date`
