#!/bin/bash

id=`date +%b%d-%H:%M`
mkdir -p $id

echo $id

function runtest {
	ntarget=10000

	for nrl in 8 16 32 64 128 256 512; do
	for us in 10 20 30 40 50; do
		echo $nrl $us
		dmesg -c > /dev/null;
		insmod ./microbench.ko ntarget=$ntarget nrl=$nrl dt_us=$us;
		dmesg >> $id/out.txt;
	done
	done
}

make > /dev/null 2>&1 && dmesg -c > /dev/null && runtest
