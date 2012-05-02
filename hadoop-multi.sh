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
for iso in "" "--inv-weighted"; do # other valid options "--enable" and "--weighted"
for nhadoop in 3; do
	subdir=size$size-iso$iso-mtu$mtu-nhadoop$nhadoop
	python tests/test_hadoop_trace.py --mtu $mtu \
		--dir /tmp/$exptid/$subdir --size $size \
		--exptid $exptid $iso --nhadoop $nhadoop
done
done
done
done

# Plot the output
pushd ~/vimal/10g/exptdata/$exptid
for dir in *; do
for ext in png pdf; do
	python2.6 ~/iso/tests/plots/plot-hadoop-trace-tenants.py --dirs $dir \
		--out $dir.$ext \
		--maxx 2500
done
done
popd

echo $start $exptid
echo hadoop-multi $exptid >> TODO

echo `date`
