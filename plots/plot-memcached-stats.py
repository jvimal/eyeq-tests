from helper import *
import plot_defaults
from collections import defaultdict
import re
from matplotlib.font_manager import FontProperties

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

parser.add_argument('--out', '-o',
                    default=None,
                    dest="out")

parser.add_argument('--mcperf',
                    default=False,
                    action="store_true",
                    dest="mcperf")

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

def parse_ops_mcperf(f):
    pat_reqr = re.compile(r'Request rate: ([0-9\.]+) req/s')
    pat_rspr = re.compile(r'Response rate: ([0-9\.]+) rsp/s')
    lines = open(f).readlines()
    reqr = 0
    rspr = 0
    for l in lines:
        m = pat_reqr.search(l)
        if m:
            reqr = float(m.group(1))
        # resp
        m = pat_rspr.search(l)
        if m:
            rspr = float(m.group(1))
    return (reqr, rspr)

def plot_ops(ax):
    i = -1
    colours=["blue", "orange", "green", "red", "magenta"]
    for f,leg in zip(args.files, args.legend):
        i += 1
        if '/' in leg:
            leg = os.path.basename(leg)
        if args.mcperf:
            reqr, rspr = parse_ops_mcperf(f)
            ax.bar([i+0.0], [reqr], 0.25, label="Req/sec %s" % (leg), color=colours[i])
            ax.bar([i+0.25], [rspr], 0.25, label="Resp/sec %s" % (leg), color=colours[i], alpha=0.5)
        else:
            values = parse_ops(f)
            ys = values['total']
            ax.plot(ys, lw=2, label=leg)
            ax.set_xlabel("Samples")
    ax.grid()
    fontP = FontProperties()
    fontP.set_size('small')
    ax.legend(loc="lower right", prop=fontP)
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

pat_mcperf = re.compile(r'([\d\.]+) (\d+)')
def parse_latency_mcperf(f):
    lines = open(f).readlines()
    skip = 0
    xvalues = []
    yvalues_cdf = []
    yvalues_pdf = []
    sum = 0

    for l in lines:
        if skip == 0 and "Response time histogram [ms]" in l:
            skip = 1
            continue

        # Parse
        l = l.strip()
        if l == ":":
            continue
        if "Response time [ms]: p25" in l:
            break

        m = pat_mcperf.search(l)
        if m:
            lo, num = m.group(1), m.group(2)
            #print lo, hi, num
            lo = float(lo)
            xvalues.append(int(lo * 1e3))
            sum += int(num)
            yvalues_cdf.append(sum)
            yvalues_pdf.append(int(num))
    yvalues_cdf = map(lambda e: e * 1.0 / sum, yvalues_cdf)
    yvalues_pdf = map(lambda e: e * 1.0 / sum, yvalues_pdf)
    return (xvalues, yvalues_cdf, yvalues_pdf)

def plot_latency(ax):
    i = -1
    ls = ['-', '-', '--', '-.', ':']
    colours=["blue", "orange", "green", "red", "magenta"]

    for f,leg in zip(args.files, args.legend):
        i += 1
        leg = leg.replace('-without-EyeQ', '')
        if args.mcperf:
            x, yc, yp = parse_latency_mcperf(f)
        else:
            x, yc, yp = parse_latency(f)
        ax.plot(x, yc, lw=4, label=leg, ls=ls[i], color=colours[i])#, marker='so^v'[i], markersize=15, markevery=300)

    ax.grid()
    fontP = FontProperties()
    fontP.set_size('large')
    ax.legend(loc="lower right", prop=fontP)
    ax.set_xlabel("Latency (us)")
    ax.set_ylabel("CDF")
    #ax.set_title(args.latency_title)
    if args.log:
        ax.set_xscale("log")

m.rc('figure', figsize=(10*2, 4.5))
fig = plt.figure()
plot_ops(fig.add_subplot(1, 2, 1))
plot_latency(fig.add_subplot(1, 2, 2))

if args.out:
    plt.savefig(args.out)
else:
    plt.show()
