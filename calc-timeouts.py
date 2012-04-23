#!/usr/bin/python
import argparse
import os

parser = argparse.ArgumentParser(description="Calculate timeouts during experiments.")
parser.add_argument('--dir', '-d',
                    dest="dir",
                    help="Directory containing netstat_{begin,end}.txt files",
                    required=True)

args = parser.parse_args()

def parse_file(f):
    ret = {}
    for line in open(f).xreadlines():
        if 'timeouts' in line:
            num, desc = line.strip().split(' ', 1)
            ret[desc] = int(num)
    return ret

begin = parse_file(os.path.join(args.dir, "netstat_begin.txt"))
end = parse_file(os.path.join(args.dir, "netstat_end.txt"))

for k in begin.keys():
    print "%10d    %s" % (end[k] - begin[k], k)
