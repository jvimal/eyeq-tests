#!/bin/bash

python test_fullmeshiperf.py --stop
python test_fullmeshiperf.py --start -P 4 --cpu 6,7 

ssh l20 "cd /usr/local/hadoop; hadoop jar hadoop-examples-0.20.205.0.jar sort random-data sorted-data-mesh-udp-onoff 2>&1" | tee /root/vimal/hadoop_udp_onoff.txt

python test_fullmeshiperf.py --stop

#ssh l20 "cd /usr/local/hadoop; hadoop jar hadoop-examples-0.20.205.0.jar sort random-data sorted-data-baseline" > /root/vimal/hadoop_udp_fullmesh_progress.txt
