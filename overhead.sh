#!/bin/bash

ctrlc() {
  killall -9 python
  exit
}

trap ctrlc SIGINT
exptid=`date +%b%d-%H:%M`

time=30
set -e

echo $exptid

for C in 1000 3000 6000 9000; do
for n in 1 16 32 64; do
for dp in tx rx; do
for iso in "" "--enable"; do
	subdir=exptdata/$exptid/$dp/n$n-C$C-iso$iso

	python tests/overhead.py \
		--rate $C \
		-n $n \
		--dir $subdir \
		-t $time \
		--datapath $dp \
		$iso

	python2.6 tests/plots/plot-overhead.py --test \
		-n $n \
		-C $C \
		$iso \
		--dp $dp \
		--dir exptdata/$exptid/ | tee -a overhead-numbers
done
done
done
done

# Also try for another VQ update interval
for C in 1000 3000 6000 9000; do
for n in 1 16 32 64; do
for dp in rx; do
for iso in "--enable"; do
for vqupdate in 50 100; do
	subdir=exptdata/$exptid/$dp/n$n-C$C-iso$iso-vqu$vqupdate

	python tests/overhead.py \
		--rate $C \
		-n $n \
		--dir $subdir \
		-t $time \
		--datapath $dp \
		$iso \
		--vqupdate $vqupdate

done
done
done
done
done


echo `date` $exptid
echo new tx rx $exptid >> TODO

for dp in rx tx; do
for ext in pdf png; do
	python2.6 tests/plots/plot-overhead.py \
		--dir exptdata/$exptid/ \
		--dp $dp \
		-o exptdata/$exptid/$dp.$ext
done
done
