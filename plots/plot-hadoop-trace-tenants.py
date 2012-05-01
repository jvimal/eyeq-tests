from helper import *
import re
from collections import defaultdict
import glob
import plot_defaults

parser = argparse.ArgumentParser("Hadoop trace plotter.")
parser.add_argument('--dirs', '-d',
                    dest='dirs',
                    nargs="+",
                    required=True)

parser.add_argument('-t', '--title',
                    dest='title',
                    default="Flow/Job completion times")

parser.add_argument('-e', '--every',
                    dest='every',
                    action="store_true",
                    default=False)

parser.add_argument('--out', '-o',
                    dest='out',
                    default=None,
                    help="Output plot to file")

parser.add_argument('--base', '-b',
                    dest='base',
                    type=int,
                    default=2,
                    help="# Connections are powers of this base")

parser.add_argument('--maxx',
                    dest="maxx",
                    type=int,
                    default=4000,
                    help="Max x axis (seconds)")

parser.add_argument('--minx',
                    dest="minx",
                    type=int,
                    default=500,
                    help="Max x axis (seconds)")

args = parser.parse_args()
plot_defaults.rcParams['figure.figsize'] = 10, 3.5

pat_start = re.compile(r'starting TCP flow seed (\d+).*size (\d+).*\-\-\-\s([\d\.]+)')
pat_end = re.compile(r'ending TCP flow seed (\d+).*\-\-\-\s([\d\.]+)')

def get_marker(tid):
    return 'oxsv'[tid]

def parse_fcts(f):
    flow_start = defaultdict(int)
    flow_end = defaultdict(int)
    flow_fct = {}
    lines = open(f).readlines()
    for line in lines:
        ms = pat_start.match(line)
        me = pat_end.match(line)
        if ms:
            fid = ms.group(1)
            size = ms.group(2)
            time = float(ms.group(3))
            flow_start[fid] = time
        if me:
            fid = me.group(1)
            time = float(me.group(2))
            flow_end[fid] = time
            flow_fct[fid] = flow_end[fid] - flow_start[fid]
            #print me.group(2), line, flow_end[fid], flow_start[fid]
            print "Flow %s completed in %.6f sec" % (fid, flow_fct[fid])
    return flow_fct

def plot_cdf(values, bin_sec=0.001, **kwargs):
    values.sort()
    curr = values[0]
    cdf_x = []
    cdf_y = []
    count = 0

    cdf_x.append(values[0] - bin_sec)
    cdf_y.append(0)

    for v in values:
        if v <= curr + bin_sec:
            count += 1
        else:
            cdf_x.append(curr + bin_sec)
            cdf_y.append(count)
            count += 1
            curr = v
    cdf_x.append(curr+bin_sec)
    cdf_y.append(count)
    fracs = map(lambda c: c*1.0/count, cdf_y)
    #print cdf_x, cdf_y, fracs
    plt.plot(cdf_x, fracs, **kwargs)
    return

def get_num_tenants(dir):
    return len(glob.glob("%s/l1/sort-*.txt" % dir))

for i,dir in enumerate(args.dirs):
    num_tenants = get_num_tenants(dir)
    print num_tenants
    for j in xrange(num_tenants):
        col = default_colours[j]
        all_values = []
        for d in glob.glob(dir + "/*"):
            print d
            fcts = parse_fcts(os.path.join(d, "sort-%d.txt" % j))
            print fcts.values()
            all_values += fcts.values()
            if args.every:
                plot_cdf(fcts.values(), alpha=0.3, color=col)
        plot_cdf(all_values, lw=4, color=col, label="P%s" % (args.base**j),
                 marker=get_marker(j), markersize=10, markevery=150)
        plt.axvline(x=max(all_values), ymin=0, ymax=1, ls='--', color=col,
                    marker=get_marker(j))

    #locs, labels = map(list, plt.xticks())

    #locs = locs[:-1] + [max(all_values)]
    #plt.xticks(locs, map(lambda e: '%.1f' % e, locs))
    yticks = map(lambda e: (e/5.0), range(0, 6))
    plt.yticks(yticks, map(lambda e: '%.1f' % e, yticks))
    xticks = range(args.minx, args.maxx+1, 500)
    plt.xticks(xticks, map(str, xticks))
    #plt.figure()

plt.title(args.title)
plt.xlabel("Seconds")
plt.ylabel("Job Progress")
plt.legend(loc="upper left")
plt.grid(True)
if args.out:
    plt.savefig(args.out)
else:
    plt.show()

