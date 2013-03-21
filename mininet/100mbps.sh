#!/bin/bash

dir=${1:-.}

pushd $dir

# Set the TX speed to 100Mb/s
tools/pi.py --set 18,98

# Set the RX speed to 98Mb/s
tools/pi.py --set 5,98

# Set the tokenbucket timeout value to 100us
tools/pi.py --set 3,100000

# Set the rate metering interval to 5ms
tools/pi.py --set 13,5000

# Trigger a recompute on every host
num_hosts=8
for i in `seq 1 $num_hosts`; do
    echo "dev h$i-eth0" > /sys/module/perfiso/parameters/recompute_dev
done

popd
