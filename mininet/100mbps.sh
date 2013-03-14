#!/bin/bash

dir=${1:-.}

pushd $dir

# Set the TX speed to 100Mb/s
tools/pi.py --set 18,98

# Set the RX speed to 92Mb/s
tools/pi.py --set 5,92

# Set the tokenbucket timeout value to 1ms
tools/pi.py --set 3,1000000

# Set the rate metering interval to 10ms
tools/pi.py --set 13,10000

# Trigger a recompute on every host
num_hosts=4
for i in `seq 1 $num_hosts`; do
    echo "dev h$i-eth0" > /sys/module/perfiso/parameters/recompute_dev
done

popd
