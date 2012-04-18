#!/bin/bash

make > /dev/null 2>&1 && dmesg -c > /dev/null && (insmod ./hrtimer.ko || dmesg)
