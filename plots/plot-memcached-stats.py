from helper import *
from collections import defaultdict
import re

parser = argparse.ArgumentParser("Memcached stats plotter.")

parser.add_argument('--files', '-f',
                    dest='files',
                    nargs="+",
                    required=True)

parser.add_argument('--legend',
                    help="Legend for plots",
                    default=None,
                    nargs="+",
                    dest="legend")

parser.add_argument('--ops-title',
                    default="Memcached Ops/sec",
                    dest="ops_title")

parser.add_argument('--latency-title',
                    default="Memcached Op-latency",
                    dest="latency_title")

parser.add_argument('--type',
                    dest="type",
                    choices=["get","set","total","all"],
                    default="total")

parser.add_argument('--log',
                    default=True,
                    dest="log")

args = parser.parse_args()
if args.legend is None:
    args.legend = args.files

spaces = re.compile(r'\s+')

def parse_ops(f):
    lines = open(f).readlines()
    state_values = defaultdict(list)
    state = ""
    for l in lines:
        l = l.strip()
        if "Get Statistics" in l:
            state = "get"
            continue
        if "Set Statistics" in l:
            state = "set"
            continue
        if "Total Statistics" in l:
            state = "total"
            continue
        if "TPS(ops/s)" in l:
            state = "store:" + state
            continue
        if "store" in state:
            state, which = state.split(":")
            state = ""
            assert("Period" in l)
            values = spaces.split(l)
            state_values[which].append(int(values[2]))
        continue

    return state_values

def plot_ops(ax):
    for f,leg in zip(args.files, args.legend):
        if '/' in leg:
            leg = os.path.basename(leg)
        values = parse_ops(f)
        ys = values['total']
        ax.plot(ys, lw=2, label=leg)
    ax.grid()
    ax.legend(loc="lower right")
    ax.set_xlabel("Samples")
    ax.set_ylabel("Ops/sec")
    ax.set_ylim(ymin=0)
    ax.set_title(args.ops_title)

pat = re.compile(r'(\d+) - \s+(\d+):\s+(\d+)')
def parse_latency(f):
    lines = open(f).readlines()
    skip = 2
    xvalues = []
    yvalues_cdf = []
    yvalues_pdf = []
    sum = 0
    for l in lines:
        if skip == 2 and l.startswith("Total Statistics ("):
            skip = 1
            continue
        elif skip == 1 and "lo_us -" in l:
            skip = 0
            continue
        elif skip:
            continue
        assert(skip == 0)
        m = pat.search(l)
        if m:
            lo, hi, num = m.group(1), m.group(2), m.group(3)
            #print lo, hi, num
            xvalues.append(int(hi))
            sum += int(num)
            yvalues_cdf.append(sum)
            yvalues_pdf.append(int(num))
    yvalues_cdf = map(lambda e: e * 1.0 / sum, yvalues_cdf)
    yvalues_pdf = map(lambda e: e * 1.0 / sum, yvalues_pdf)
    return (xvalues, yvalues_cdf, yvalues_pdf)

def plot_latency(ax):
    for f,leg in zip(args.files, args.legend):
        x, yc, yp = parse_latency(f)
        ax.plot(x, yc, lw=2, label=leg)

    ax.grid()
    ax.legend(loc="lower right")
    ax.set_xlabel("Latency (us)")
    ax.set_ylabel("CDF")
    ax.set_title(args.latency_title)
    if args.log:
        ax.set_xscale("log")

m.rc('figure', figsize=(16, 6))
fig = plt.figure()
plot_ops(fig.add_subplot(1, 2, 1))
plot_latency(fig.add_subplot(1, 2, 2))
plt.show()
