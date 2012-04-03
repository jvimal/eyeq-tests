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

for mtu in 9000; do
for size in 10T; do
for iso in "" "--enable" "--weighted" "--inv-weighted"; do
for nhadoop in 3; do
	subdir=size$size-iso$iso-mtu$mtu-nhadoop$nhadoop
	python tests/test_hadoop_trace.py --mtu 9000 \
		--dir /tmp/$exptid/$subdir --size $size \
		--exptid $exptid $iso --nhadoop $nhadoop
done
done
done
done

# Plot the output
pushd ~/vimal/10g/exptdata/$exptid
for dir in *; do
	python2.6 ~/iso/tests/plots/plot-hadoop-trace-tenants.py --dirs $dir --out $dir.png
done
popd

echo $start $exptid
echo `date`
