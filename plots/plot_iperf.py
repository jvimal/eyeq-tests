import sys

sys.path += ['/home/jvimal/proj/perfiso_10g_linux/tests/plots']

from helper import *
import re
import os

pat = re.compile(r'([\d\.]+ .)bits/sec')

parser = argparse.ArgumentParser()

parser.add_argument('-f',
                    dest='files',
                    nargs="+",
                    required=True)

parser.add_argument('-o',
                    dest='out',
                    default=None)

args = parser.parse_args()

def parse_rate(s):
    num = float(s.split(' ')[0])
    f = 1
    if s.endswith('K'):
        f = 1e3
    if s.endswith('M'):
        f = 1e6
    if s.endswith('G'):
        f = 1e9
    return f*num

def parse_iperf(fname):
    ret = []
    for line in open(fname).readlines():
        m = pat.search(line)
        if m:
            ret.append(parse_rate(m.group(1))/1e6)
    return ret

for f in args.files:
    data = parse_iperf(f)
    fname = os.path.basename(f)
    plt.plot(data, lw=2, label=fname)

plt.grid()
plt.legend()

if args.out:
    plt.savefig(args.out)
else:
    plt.show()
