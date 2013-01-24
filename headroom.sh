#!/bin/bash

python tests/test_tcp2vs32.py --dir /tmp/headroom --enable -t 120 --vqrate 10000 --wtcp 2 &
sleep 40 &
tools/pi.py --set 4,9000
wait

python2.6 ~/iso/tests/plots/plot_tenant_rate.py -f \
    /tmp/headroom/tenant.txt --accum 100 --rx -o /tmp/headroom/rx.png -l TCP1 TCP32 --nototal --range 0:60 --title ""
