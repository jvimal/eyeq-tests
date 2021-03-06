#!/bin/bash

exptid=`date +%b%d-%H:%M`
time=30
start=`date`
rootdir=$(dirname `readlink -f ${BASH_SOURCE[0]}`)

ctrlc() {
	killall -9 python
	exit
}

trap ctrlc SIGINT

n=3

for topo in $rootdir/allocation_topos/*; do
	t=$(basename $topo)
for rate in 9000; do
	python tests/test_allocation.py --dir /tmp/alloc-$rate-topo$t \
		--vqrate $rate \
		--exptid $exptid \
		--topo $topo
done
done

echo exptid $exptid

pushd ../exptdata/$exptid

for dir in *; do
for host in $dir/*; do
	host=`basename $host`
	python2.6 ~/iso/tests/plots/plot_tenant_rate.py \
		-f $dir/$host/tenant.txt \
		--tx \
		--every 20 \
		-o $dir/tx-$host.png \
		-l `seq 1 $n | tr "\n" ' '`

	python2.6 ~/iso/tests/plots/plot_tenant_rate.py \
		-f $dir/$host/tenant.txt \
		--rx \
		--every 20 \
		-o $dir/rx-$host.png \
		-l `seq 1 $n | tr "\n" ' '`
done
done
