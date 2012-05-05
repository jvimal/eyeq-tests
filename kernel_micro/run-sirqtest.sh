#!/bin/bash

make > /dev/null 2>&1 && dmesg -c > /dev/null && (insmod ./sirq_test.ko)
sleep 9
rmmod sirq_test
dmesg

