#!/bin/bash

exptid=`date +%b%d-%H:%M`
time=120
start=`date`
ntenant=2
cpubind=""
# cpubind="--bind"

set -e

ctrlc() {
	killall -9 python
	exit
}

trap ctrlc SIGINT

echo exptid $exptid

for size in 10K 100K 1M; do
for iso in "" "--enable"; do
	subdir=paggr-size$size-iso$iso
	python tests/test_partition_aggregate.py -n $ntenant \
		--size $size \
		--dir /tmp/$exptid/$subdir \
		--exptid $exptid \
		--repeat 30000 \
		$iso $cpubind
done
done

pushd ../exptdata/$exptid
for dir in *; do
for ext in pdf png; do
	mkdir -p graphs/$ext

	python2.6 ~/iso/tests/plots/plot-paggr-xput-latency.py --bin 1e-6 \
		--title "Partition Aggregate ($dir)" \
		-o graphs/$ext/$dir.$ext \
		--dir $dir

	python2.6 ~/iso/tests/plots/plot_rate.py \
		-f $dir/l1/net.txt \
		-o graphs/$ext/txrate-$dir.$ext

	python2.6 ~/iso/tests/plots/plot_rate.py \
		-f $dir/l1/net.txt \
		-o graphs/$ext/rxrate-$dir.$ext \
		--rx

done
done
popd

echo $start $exptid
echo `date`

exit 0
