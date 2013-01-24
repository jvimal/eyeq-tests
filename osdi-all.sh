#!/bin/bash

# Invoking OSDI experiments

###########################################
# Micro evaluations
###########################################

function micro_overhead {
	bash tests/overhead.sh
}

function micro_convergence {
	bash tests/incast.sh
}

# Micro: bursty (TODO)
function micro_bursty {
	bash tests/incast-onoff.sh
}


###########################################
# Macro evaluations
###########################################

function macro_multihadoop {
	bash tests/hadoop-multi.sh
	bash tests/hadoop-multi-10T.sh
}

function macro_memcached_high {
	bash tests/memcached_cluster_onoff.sh 6000
}

function macro_memcached_low {
	bash tests/memcached_cluster_onoff.sh 3000
}

function macro_xen_latency {
	# TODO
	echo TODO
}

macro_multihadoop
macro_memcached_high
macro_memcached_low
for i in {1..3}; do
	micro_overhead
done
