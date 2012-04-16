from helper import *
import re
from collections import defaultdict
import glob

parser = argparse.ArgumentParser("Plot results of partition-aggregate colocated workload.")
parser.add_argument('--dir', '-d',
                    dest='dir',
                    required=True)

parser.add_argument('-t', '--title',
                    dest='title',
                    default="Multi-tenant Partition Aggregate")

parser.add_argument('--out', '-o',
                    dest='out',
                    help="Output plot to file")

parser.add_argument('--bin',
                    dest='bin',
                    type=float,
                    default=1e-3,
                    help="bin size for CDF")

maxx = {
    '10K': 0.02,
    '100K': 0.02,
    '1M': 0.4,
}

args = parser.parse_args()
pat_usec = re.compile(r'sec: ([0-9]+), usec: ([0-9]+)')
pat_size = re.compile(r'size([0-9]+[KM])-')

def parse_fcts(f):
    print 'Parsing file %s' % f
    lines = open(f).xreadlines()
    iter = 0
    fcts = []
    for line in lines:
        m = pat_usec.search(line)
        if m:
            sec = int(m.group(1))
            usec = int(m.group(2))
            iter += 1
            fcts.append(sec + usec * 1e-6)
    print '%d iterations in file' % iter
    return fcts

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

dir = os.path.join(args.dir, "l1")
print "searching in %s" % dir
max_x = 0.02

for i,f in enumerate(sorted(glob.glob(dir + "/paggr*.txt"))):
    try:
        fcts = parse_fcts(f)
    except:
        print 'could not parse %s' % f
        continue
    #print fcts
    m = pat_size.search(f)
    if m:
        size = m.group(1)
        max_x = maxx[size]

    if len(fcts):
        filename = os.path.basename(f)
        plot_cdf(fcts, bin_sec=args.bin, lw=2, label=filename)

plt.title(args.title)
plt.xlim((0, max_x))
plt.xlabel("Seconds")
plt.ylabel("CDF/Fraction")
plt.legend(loc="upper left")
plt.legend(loc="center right")
plt.grid()
if args.out:
    plt.savefig(args.out)
else:
    plt.show()
