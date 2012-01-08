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

parser.add_argument('--title',
                    default="Memcached Ops/s",
                    dest="title")

parser.add_argument('--type',
                    dest="type",
                    choices=["get","set","total","all"],
                    default="total")

args = parser.parse_args()
if args.legend is None:
    args.legend = args.files

spaces = re.compile(r'\s+')

def parse(f):
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

for f,leg in zip(args.files, args.legend):
    if '/' in leg:
        leg = os.path.basename(leg)
    values = parse(f)
    ys = values['total']
    plt.plot(ys, lw=2, label=leg)
    #plt.plot(x, yp, label=leg, lw=2)

plt.grid()
plt.legend(loc="lower right")
plt.xlabel("Samples")
plt.ylabel("Ops/sec")
plt.ylim(ymin=0)
plt.title(args.title)

plt.show()
