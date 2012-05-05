#!/bin/bash

make > /dev/null 2>&1 && dmesg -c > /dev/null && (insmod ./tasklet_test.ko)
sleep 2
rmmod tasklet_test
dmesg

