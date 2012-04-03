#!/usr/bin/env python
from collections import defaultdict
from helper import *
import os
import glob
import sys
import plot_defaults
import re

parser = argparse.ArgumentParser()
parser.add_argument('-d',
                    help="Directories containing output files",
                    required=True,
                    action="store",
                    nargs='+',
                    dest="dirs")

args = parser.parse_args()

pat_time = re.compile(r'(\d+) us')
pat_params = re.compile('(\w+=\d+)')

data = defaultdict(list)
all_nrl = set([])
all_dt_us = set([])
all_labels = set([])

def val(pstr):
    return int(pstr.split('=')[1])

def parse_file(f):
    global data
    params = None
    state = 0
    type = None
    values = []
    nrl, ntarget, dt_us = None, None, None
    for line in open(f).readlines():
        if '***' in line:
            if len(values):
                print nrl, ntarget, dt_us, values
                data[(nrl,ntarget,dt_us)].append(values)
                all_nrl.add(nrl)
                all_dt_us.add(dt_us)
            values = {}
            m = pat_params.findall(line)
            if m:
                nrl, ntarget, dt_us, dt_work = map(lambda e: int(e.split('=')[1]), m)
                state = 1

        else:
            if state == 1:
                type = line.split(']')[1].strip()
                state = 2

            if state == 2:
                m = pat_time.search(line)
                if m:
                    value = int(m.group(1))
                    scaled = float(value) / (ntarget * dt_us)
                    state = 1
                    #values.append((type, scaled))
                    values[type] = scaled
                    all_labels.add(type)

def select(lst, name):
    ret = []
    for row in lst:
        for e in row:
            if e[0] == name:
                ret.append(e[1])
                break
    return ret

def eq(a, b):
    def eqele(a, b):
        return a is None or b is None or a == b
    t1 = zip(a, b)
    t2 = map(lambda (a,b): eqele(a, b), t1)
    t3 = reduce(lambda a,b: a*b, t2)
    return t3

def get_group(tup):
    ret = []
    for k in sorted(data.keys()):
        if eq(tup, k):
            ret.append(data[k])
    return ret

def collect(lst):
    ret = defaultdict(list)
    for d in lst:
        for k in d.keys():
            ret[k].append(d[k])
    return ret

for d in args.dirs:
    parse_file('%s/out.txt' % d)

ntarget = 10000
start = 0

def dofig(dt_us):
    legend = []
    for j,label in enumerate(sorted(list(all_labels))):
        values = []
        errvalues = []
        for i,nrl in enumerate(sorted(all_nrl)):
            d = collect(data[(nrl,ntarget,dt_us)])
            for k in d.keys():
                if k != label:
                    continue
                values.append(avg(d[k]))
                errvalues.append(stdev(d[k]))
                #errvalues.append((min(d[k]), max(d[k])))
        w = len(all_labels)+1
        xvalues = range(j, j+w*len(values), w)
        p = plt.bar(xvalues, values, 1, color=default_colours[j],
                    yerr=errvalues, ecolor='black')
        legend.append((p[0], label))
    plt.legend(map(first, legend), map(second, legend), loc='upper left')
    plt.xticks(range(w/2, len(all_nrl)*w, w),
               sorted(list(all_nrl)))

for dt_us in sorted(all_dt_us):
    dofig(dt_us)
    plt.ylabel("Scaled completion time")
    plt.xlabel("Number of RLs")
    plt.grid(True)
    plt.title("dt=%dus" % dt_us)
    plt.figure()
    continue

    list_xvalues = []
    list_yvalues = []
    list_legend = []
    for i,nrl in enumerate(sorted(all_nrl)):
        values = []
        #print nrl, dt_us, collect(data[(nrl,10000,dt_us)])
        d = collect(data[(nrl, ntarget, dt_us)])
        labels = list(sorted(d.keys()))
        w = len(labels)
        for k in labels:
            xvalues = range(start, start+w*len(values), w)
            values.append(avg(d[k]))

        print nrl, dt_us, xvalues, values
        #plt.bar(xvalues, values, 1, color=default_colours[i])
        print labels
        start += 1
        break
    break

plt.show()

