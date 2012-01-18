#!/usr/bin/env python
from collections import defaultdict
from helper import *
import os
import glob
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--files', '-f',
                    help="Rate timeseries output to one plot",
                    required=True,
                    action="store",
                    nargs='+',
                    dest="files")

parser.add_argument('--out', '-o',
                    help="Output png file for the plot.",
                    default=None, # Will show the plot
                    dest="out")

parser.add_argument('--maxy',
                    help="Max mbps on y-axis..",
                    default=1000,
                    action="store",
                    dest="maxy")

parser.add_argument('--miny',
                    help="Min mbps on y-axis..",
                    default=0,
                    action="store",
                    dest="miny")

parser.add_argument('--title',
                    help="Plot title",
                    default="Rates",
                    action="store",
                    dest="title")

parser.add_argument('--accum',
                    help="How many seconds to accumulate to compute average",
                    default=None,
                    type=int,
                    action="store",
                    dest="accum")

m.rc('figure', figsize=(16, 6))
args = parser.parse_args()
LOADGEN_OUTPUT = 'loadgen'

def parse_loadgen_file(f):
    dir = os.path.dirname(f)
    files = glob.glob(dir + "/%s*.txt" % LOADGEN_OUTPUT)
    ret = {}
    tid = -1
    print files
    for f in sorted(files):
        tid += 1
        lines = open(f).readlines()
        for l in lines:
            if l[0] not in '0123456789':
                continue
            try:
                t, rx, tx, blah1, blah2 = map(float, l.strip().split(' '))
            except:
                print 'error, ignoring line:', f, l
                continue
            if not ret.has_key(tid):
                ret[tid] = defaultdict(list)
            ret[tid]['t'].append(t)
            ret[tid]['rx'].append(rx)
            ret[tid]['tx'].append(tx)
        print 'parsed file %s' % f
    return ret

def parse_file(f):
    if 'tenant.txt' not in f:
        return parse_loadgen_file(f)
    lines = open(f).readlines()
    start_time = 0
    ret = {}
    for l in lines:
        if l.startswith('#'):
            continue
        t, tid, tx, rx = l.split(',')
        t, tx, rx = map(float, [t, tx, rx])
        if start_time == 0:
            start_time = t
        if not ret.has_key(tid):
            ret[tid] = defaultdict(list)
        ret[tid]['t'].append(t - start_time)
        ret[tid]['tx'].append(tx)
        ret[tid]['rx'].append(rx)
    print 'parsed file %s' % f
    return ret

def accum(values):
    if args.accum is None or args.accum == 1:
        return values
    ret = []
    count = 0
    tot = 0
    for v in values:
        tot += v
        count += 1
        if count == args.accum:
            ret.append(tot*1.0/args.accum)
            count = 0
            tot = 0
    return ret

# Plots either tx/rx for all tenants on a particular server (one tenant.txt file)
def plot_rate(ax, data, dir="tx", title="Rate"):
    total = []
    TID = -1
    default_colours = 'grb'
    for tid in sorted(data.keys()):
        #if tid != '11.0.1.1':
        #    continue
        TID += 1
        xvalues = accum(data[tid]['t'])
        yvalues = accum(data[tid][dir])
        ax.plot(xvalues, yvalues, lw=2, label=str(tid), color=default_colours[TID])
        if len(total) == 0:
            total = yvalues
        else:
            total = map(sum, zip(total, yvalues))

    if len(total):
        l = min(len(total), len(xvalues))
        ax.plot(xvalues[0:l], total[0:l], lw=2, label="total", color='b')
    try:
        ax.legend(loc='lower right')
    except:
        pass
    ax.set_title(title)
    ax.grid()
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Mbps")
    ax.set_ylim((0, 10001))
    return

for f in args.files:
    data = parse_file(f)
    fig = plt.figure()
    for col, dir in enumerate("tx,rx".split(',')):
        ax = fig.add_subplot(1, 2, col)
        plot_rate(ax, data, dir, title="%s rate" % dir)

plt.show()
