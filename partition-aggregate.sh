#!/bin/bash

exptid=`date +%b%d-%H:%M`
time=120
start=`date`
ntenant=2

ctrlc() {
	killall -9 python
	exit
}

trap ctrlc SIGINT

echo exptid $exptid

for size in 10K 100K 1M; do
for iso in "" "--enable"; do
	subdir=size$size-iso$iso
	python tests/test_partition_aggregate.py -n $ntenant \
		--size $size \
		$iso
done
done

echo $start $exptid
echo `date`
