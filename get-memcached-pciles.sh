#!/bin/bash

files="mcperf-0-*.txt mcperf-1-*.txt mcperf-2-*.txt mcperf-3-*.txt"

function get_pciles {
    ls $1
    (for file in `find $1 -type f -iname 'mcperf*'`; do
    	grep 'Response time \[ms\]: p2' $file
    done) | less | awk '{ pc50 += $7; } END { print "50pc", pc50/NR; }'
    (for file in `find $1 -type f -iname 'mcperf*'`; do
    	grep 'Response time \[ms\]: p9' $file
    done) | awk '{ pc95 += $5; pc99 += $7; pc999 += $9 } END { print "95pc", pc95/NR, "99pc", pc99/NR, "99.9pc", pc999/NR; }'
}

for workload in ~/vimal/exports/memcached_cluster/*; do
   work=$(basename $workload)
    for tenant in mem udp,mem; do
    for iso in "--enable" ""; do
	dir=memcached-mtu9000-iso$iso-work$work-active$tenant
	echo $dir
	get_pciles $dir
    done
   done
done

