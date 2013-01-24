#!/bin/bash

(for file in `find . -type f -iname 'mcperf-*'`; do
	#echo $file;
	grep -i 'request rate' $file | awk '{ print $3 }'
done) | awk '{ print $1; sum += $1 } END { print sum }'

