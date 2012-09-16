#!/bin/bash

ctrlc() {
	killall -9 python
	exit
}


trap ctrlc SIGINT
exptid=`date +%b%d-%H:%M`
t=120

echo $exptid

for C in 5000; do
for n in 1 100 1000 10000; do
for rl in newrl htb; do
	subdir=exptdata/$exptid/rl$rl-n$n-C$C
	python tests/rl-overhead.py \
		--rate $C \
		-n $n \
		--dir $subdir \
		-t $t
done;
done;
done

echo `date` $exptid
echo rl stress $exptid >> TODO
