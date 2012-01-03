from helper import *
import re

parser = argparse.ArgumentParser("Memcached histogram plotter.")

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
                    default="Memcached Latency",
                    dest="title")

parser.add_argument('--log',
                    default=True,
                    dest="log")

args = parser.parse_args()
if args.legend is None:
    args.legend = args.files

pat = re.compile(r'(\d+) - \s+(\d+):\s+(\d+)')

def parse(f):
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

for f,leg in zip(args.files, args.legend):
    x, yc, yp = parse(f)
    plt.plot(x, yc, lw=2, label=leg)
    #plt.plot(x, yp, label=leg, lw=2)

plt.grid()
plt.legend(loc="lower right")
plt.xlabel("Latency (us)")
plt.ylabel("CDF")
plt.title(args.title)

if args.log:
    plt.xscale("log")

plt.show()
