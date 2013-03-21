#!/bin/bash

ip=$1
conn=$2

if [ -z "$ip" ] || [ -z "$conn" ]; then
    echo missing ip, connections.  usage $0 ipaddr total-conn
    exit
fi

~/libmemcached-1.0.16/clients/memaslap \
	-s $ip -S 1s \
	-F mininet/memaslap.cnf \
	--threads=$conn --concurrency=$conn --conn_sock=1
