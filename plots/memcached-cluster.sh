#!/bin/bash

for work in get-6k.cnf set-6k.cnf; do
for iso in "" "--enable"; do
for active in mem udp udp,mem; do
	file=serv-iso$iso-work$work-active$active.png
	plot_rate.py -f \
		memcached-mtu9000-iso$iso-work$work-active$active/l{1,2,3,4}/net.txt \
		-i total  -l l1 l2 l3 l4 \
		--title "TX rates at $active servers iso$iso" -o $file

	file=client-iso$iso-work$work-active$active.png
	plot_rate.py -f \
		memcached-mtu9000-iso$iso-work$work-active$active/l{5,6,7,8}/net.txt \
		-i total  -l l5 l6 l7 l8 \
		--rx \
		--title "RX rates at $active clients iso$iso" -o $file
done
done
done
