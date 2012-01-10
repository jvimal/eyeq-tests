#!/usr/bin/env python
from collections import defaultdict
from helper import *

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

m.rc('figure', figsize=(16, 6))
args = parser.parse_args()

def parse_file(f):
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
    return ret

# Plots either tx/rx for all tenants on a particular server (one tenant.txt file)
def plot_rate(ax, data, dir="tx", title="Rate"):
    total = []
    for tid in sorted(data.keys()):
        xvalues = data[tid]['t']
        yvalues = data[tid][dir]
        ax.plot(xvalues, yvalues, lw=2, label=tid)
        if len(total) == 0:
            total = yvalues
        else:
            total = map(sum, zip(total, yvalues))

    if len(total):
        ax.plot(xvalues, total, lw=2, label="total")
    ax.legend(loc='lower right')
    ax.set_title(title)
    ax.grid()
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Mbps")
    return

for f in args.files:
    data = parse_file(f)
    fig = plt.figure()
    for col, dir in enumerate("tx,rx".split(',')):
        ax = fig.add_subplot(1, 2, col)
        plot_rate(ax, data, dir, title="%s rate" % dir)

plt.show()
