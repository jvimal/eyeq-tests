#!/usr/bin/python
import sys
import argparse
import termcolor as T
import re
from collections import defaultdict
from helper import *
import plot_defaults
import matplotlib as mp

parser = argparse.ArgumentParser(description="Plot netperf experiment outputs.")
parser.add_argument('--rr',
                    nargs="+",
                    help="rr files to parse")

parser.add_argument('--legend',
                    nargs="+",
                    help="labels for the rr files")

parser.add_argument('--out', '-o',
                    help="save plot to file")

parser.add_argument('--ymin',
                    type=float,
                    help="zoom into (ymin,1) on yaxis")

parser.add_argument('--xlim',
                    default="100,1000",
                    help="xlimits")

parser.add_argument('--xlog',
                    action="store_true",
                    help="plot x-axis in logscale")

args = parser.parse_args()
rspaces = re.compile(r'\s+')

def cdf(lst):
    vals = []
    nums = []
    cum = 0
    for val, num in lst:
        cum += num
        vals.append(val)
        nums.append(cum)
    return vals, map(lambda n: n*1.0/cum, nums)

def plot_cdf(x, y, **opts):
    #plt.figure()
    plt.plot(x, y, **opts)
    #plt.show()

class RRParser:
    def __init__(self, filename):
        self.filename = filename
        self.lines = open(filename).readlines()
        self.done = False
        try:
            self.parse()
            self.done = True
        except Exception, e:
            print 'error parsing %s' % filename
            print 'exception', e

    def parse(self):
        tps_line = self.lines[6]
        fields = rspaces.split(tps_line)
        self.tps = float(fields[5])
        try:
            self.cpu_local = float(fields[6])
            self.cpu_remote = float(fields[7])
        except:
            pass

        lat_line = self.lines[11]
        fields = rspaces.split(lat_line)
        self.latency = float(fields[4])
        self.mbps_out = float(fields[6])
        self.mbps_in = float(fields[7])
        self.parse_histogram()
        return

    def parse_histogram(self):
        unit = 1
        rsep = re.compile(r':\s+')
        ret = defaultdict(int)
        def parse_buckets(line):
            nums = line.split(":", 1)[1]
            nums = map(lambda e: int(e.strip()),
                       rsep.split(nums))
            return nums
        for lno in xrange(14, 22):
            nums = parse_buckets(self.lines[lno])
            for i,n in enumerate(nums):
                ret[unit+i*unit] += n
            unit *= 10
        ret = sorted(list(ret.iteritems()))
        self.histogram = ret
        return ret

def plot():
    markers='so'
    for f,label,marker in zip(args.rr, args.legend, markers):
        r = RRParser(f)
        if not r.done:
            continue
        c = cdf(r.histogram)
        plot_cdf(c[0], c[1], lw=2, label=label, marker=marker, markersize=15)
    #print plt.figure(1).get_axes()
    #plt.figure(1).get_axes()[0].yaxis.set_major_locator(mp.ticker.MaxNLocator(20))
    #plt.figure(1).get_axes()[0].xaxis.set_major_locator(mp.ticker.MaxNLocator(20))
    xticks = range(0, 1001, 100)
    yticks = map(lambda e: e/100.0, range(50, 101, 5))
    xticklabels = map(lambda e: "%s" % e if e%200 == 0 else ' ', xticks)
    yticklabels = map(lambda e: "%.1f" % e if int(e*100)%10 == 0 else ' ', yticks)
    plt.xticks(xticks, xticklabels)
    plt.yticks(yticks, yticklabels)
    plt.axhline(lw=1, color='r', y=0.99)
    plt.legend(loc="center right")
    plt.grid(True)
    plt.xlabel("usec")
    plt.ylabel("fraction")
    plt.xlim(tuple(map(int, args.xlim.split(','))))
    if args.xlog:
        plt.xscale("log")
    if args.ymin is not None:
        plt.ylim((args.ymin, 1))
    if args.out is None:
        plt.show()
    else:
        print 'saved to %s' % args.out
        plt.savefig(args.out)

plot()
