import argparse
import glob
import sys
from collections import defaultdict
import termcolor as T
import plot_defaults
import matplotlib.pyplot as plt
import numpy as np

parser = argparse.ArgumentParser("Memcached stats plotter.")

parser.add_argument('--dir', '-d',
                    dest='dir',
                    required=True)

parser.add_argument('--out', '-o',
                    dest='out',
                    required=True)

args = parser.parse_args()

workloads = ["set-6k.cnf"]
tenants = ["mem", "udp,mem"]
isos = ["", "--enable"]
pciles = 'p50,p75,p95,p99,p999'.split(',')
pciles_labels = dict()
for p in pciles:
    s = p.replace('p','')
    if s == "999":
        s = "99.9"
    s = "%s" % s
    pciles_labels[p] = s + "p"
colours = '#ffffff,#dddddd,#aaaaaa,#777777,#eeeeee'.split(',')

series = defaultdict(list)
xaxis = "Bare,Bare\n+EyeQ,UDP,UDP\n+EyeQ".split(',')

def parse_stats(f):
    ret = defaultdict(float)
    for l in open(f).xreadlines():
        if 'Response time [ms]: p' not in l:
            continue
        data = l.split(':')[1].strip()
        data = data.split(' ')
        kvs = zip(data[0::2], data[1::2])
        for k, v in kvs:
            ret[k] = float(v)
    return ret

def avg(lst):
    return sum(lst) * 1.0 / len(lst)

def summarise(stats):
    ret = defaultdict(float)
    for k in stats.keys():
        ret[k] = avg(stats[k]) * 1000
    return ret

def dprint(d):
    for k in pciles:
        print "%4s: %8.2f us" % (k, d[k])
    return

for w in workloads:
    x = 0
    for t in tenants:
        for i in isos:
            dir = "memcached-mtu9000-iso%s-work%s-active%s" % (i, w, t)
            agg_stats = defaultdict(list)
            def aggregate(s):
                for k in s.keys():
                    if s[k] != 0.0:
                        agg_stats[k].append(s[k])
                return
            for fname in glob.glob(args.dir + "/" + dir + "/*/mcperf*"):
                stats = parse_stats(fname)
                aggregate(stats)
            agg_stats = summarise(agg_stats)
            print T.colored(dir, "green")
            dprint(agg_stats)
            for k in pciles:
                series[k].append(agg_stats[k])
            x += 1

fig, (ax, ax2) = plt.subplots(2, 1, sharex=True)

for i,k in enumerate(reversed(pciles)):
    print k, series[k]
    #plt.plot(range(0, 4), series[k], lw=2, label=k)
    for a in [ax, ax2]:
        a.bar(left=range(0, 4), height=series[k],
              bottom=1.0, width=0.8, color=colours[i],
              label=pciles_labels[k])

ax.set_yscale("log")
ax2.set_yscale("log")

if 0:
    ax2.set_ylim(10,4000)
    ax.set_ylim(50000, 1200000)
else:
    ax2.set_ylim(100,10000)
    ax.set_ylim(20000, 7 * 1000 * 1000)

ax.legend(loc="upper left")
ax.spines['bottom'].set_visible(False)
ax2.spines['top'].set_visible(False)

ax.xaxis.tick_top()
ax.tick_params(labeltop="off")
ax2.xaxis.tick_bottom()

#ax.text(3, 80, '70ms', size=12)
#plt.subplots_adjust(wspace=0.15)

plt.xticks(0.4+np.arange(0, 4), xaxis, rotation=0)
plt.ylabel("Latency (us)")
#plt.legend()
#plt.grid(True)
#plt.yscale("log")
plt.savefig(args.out)
