#!/usr/bin/env python
from collections import defaultdict
from helper import *
import os
import glob
import sys
import plot_defaults

parser = argparse.ArgumentParser()
parser.add_argument('--files', '-f',
                    help="Rate timeseries output to one plot",
                    required=True,
                    action="store",
                    nargs='+',
                    dest="files")

parser.add_argument('-l',
                    help="Labels",
                    required=True,
                    action="store",
                    nargs='+',
                    dest="labels")

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

parser.add_argument('--rx',
                    help="Plot just RX",
                    default=False,
                    action="store_true",
                    dest="rx")

parser.add_argument('--tx',
                    help="Plot just tx",
                    default=False,
                    action="store_true",
                    dest="tx")

parser.add_argument('--accum',
                    help="How many seconds to accumulate to compute average",
                    default=None,
                    type=int,
                    action="store",
                    dest="accum")

parser.add_argument('--every',
                    help="How often should the marker be placed?",
                    default=5,
                    type=int,
                    action="store",
                    dest="every")

parser.add_argument('--range',
                    help="Plot specific x-axis range (useful for zoom-in plots)",
                    default=None,
                    action="store",
                    dest="range")

parser.add_argument('--nototal',
                    help="plot total",
                    default=False,
                    action="store_true",
                    dest="nototal")

parser.add_argument('--rect',
                    help="Make graph bounding box more rectangular",
                    default=False,
                    action="store_true",
                    dest="rect")

args = parser.parse_args()
LOADGEN_OUTPUT = 'loadgen'

cols = 2
if args.rx == True or args.tx == True:
    cols = 1
    print 'cols = %d, tx/rx: %s/%s' % (cols, args.tx, args.rx)

m.rc('figure', figsize=(cols * 8, 6))

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

def get_marker(tid):
    return 'so^v'[tid]

def get_tid_from_ip(ip):
    return int(ip.split('.')[2])

# Plots either tx/rx for all tenants on a particular server (one tenant.txt file)
def plot_rate(ax, data, dir="tx", title=args.title, markevery=args.every):
    total = []
    TID = -1
    default_colours = 'grb'
    for tid in sorted(data.keys()):
        #if tid != '11.0.1.2':
        #    continue
        TID = get_tid_from_ip(tid)-1
        xvalues = accum(data[tid]['t'])
        yvalues = accum(data[tid][dir])
        label = str(tid)
        if args.labels:
            label = args.labels[TID]
        ax.plot(xvalues, yvalues, lw=2, label=label, color=default_colours[TID],
                marker=get_marker(TID), markevery=markevery, markersize=15)
        if len(total) == 0:
            total = yvalues
        else:
            total = map(sum, zip(total, yvalues))

    if len(total) and not args.nototal:
        l = min(len(total), len(xvalues))
        ax.plot(xvalues[0:l], total[0:l], lw=2, label="total", color='b')
    try:
        ax.legend(loc="center left", prop=fontP)
        #ax.legend(loc='lower right')
    except:
        pass
    ax.set_title(title)
    ax.grid(True)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Rate")
    ax.set_ylim((0, 10001))
    ax.set_yticks(range(1000, 10001, 2000))
    ax.set_yticklabels(map(lambda e: '%dG' % (e/1000), range(1000, 10001, 2000)))
    if args.range:
        try:
            lo,hi = map(float, args.range.split(':'))
            ax.set_xlim((lo, hi))
        except:
            pass
    return

if args.rect:
    plot_defaults.rcParams['figure.figsize'] = 10, 4

for f in args.files:
    data = parse_file(f)
    fig = plt.figure()
    for col, dir in enumerate("rx,tx".split(',')):
        if dir == "tx" and args.rx == True:
            continue
        if dir == "rx" and args.tx == True:
            continue
        print 'plotting %s' % dir
        ax = fig.add_subplot(1, cols, col)
        plot_rate(ax, data, dir)

if args.out:
    print 'saved to', args.out
    plt.savefig(args.out)
else:
    plt.show()
