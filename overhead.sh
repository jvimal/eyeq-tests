#!/bin/bash

ctrlc() {
  killall -9 python
  exit
}

trap ctrlc SIGINT
exptid=`date +%b%d-%H:%M`

time=100
set -e

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
		--datapath $dp
done
done
done
done

echo `date` $exptid
echo new tx rx $exptid >> TODO
