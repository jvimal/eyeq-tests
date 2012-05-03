#!/usr/bin/python
import argparse
import os

parser = argparse.ArgumentParser(description="Calculate timeouts during experiments.")
parser.add_argument('--dir', '-d',
                    dest="dir",
                    nargs="+",
                    help="Directory containing netstat_{begin,end}.txt files",
                    required=True)

parser.add_argument('-a',
                    dest="aggr",
                    help="sum all timeouts",
                    action="store_true",
                    default=False)

args = parser.parse_args()

def parse_file(f):
    ret = {}
    for line in open(f).xreadlines():
        if 'timeouts' in line:
            num, desc = line.strip().split(' ', 1)
            ret[desc] = int(num)
    return ret

total = 0
for dir in args.dir:
    begin = parse_file(os.path.join(dir, "netstat_begin.txt"))
    end = parse_file(os.path.join(dir, "netstat_end.txt"))

    for k in begin.keys():
        timeouts = end[k] - begin[k]
        if not args.aggr:
            print "%10d    %s" % (timeouts, k)
        else:
            total += timeouts
    print dir, total
print 'total', total
