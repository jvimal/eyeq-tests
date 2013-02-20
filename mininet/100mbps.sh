#!/bin/bash

# Set the interface speed to 100Mb/s
tools/pi.py --set 18,100

# Set the receive speed to 100Mb/s
tools/pi.py --set 5,100

# Set the tokenbucket timeout value to 1ms
tools/pi.py --set 3,1000000

# Set the rate metering interval to 1ms
tools/pi.py --set 13,10000

# Trigger a recompute on every host
num_hosts=3
for i in `seq 1 $num_hosts`; do
        echo "dev h$i-eth0 11.0.1.$i weight 1" > /sys/module/perfiso/parameters/set_txc_weight
        echo "dev h$i-eth0 11.0.1.$i weight 1" > /sys/module/perfiso/parameters/set_vq_weight
done
