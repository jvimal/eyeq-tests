from helper import *
from host import *
import re

parser = argparse.ArgumentParser("TCP vs UDP test plotter")

parser.add_argument('--dir',
                    dest='dir',
                    help="directory containing the $host/net.txt files",
                    required=True)

parser.add_argument('-n',
                    dest="n",
                    type=int,
                    help="Number of udp hosts in the experiment.",
                    required=True)

parser.add_argument('--out', '-o',
                    dest='out',
                    help="save output to file",
                    default=None)

TX=0
RX=1

args = parser.parse_args()

def parse_rate(fname, iface, type=TX):
    data = read_list(fname)
    values = []
    column = 2
    if type == RX:
        column = 3
    for row in data:
        try:
            ifname = row[1]
        except:
            break
        if ifname != iface:
            continue
        try:
            values.append(float(row[column]) * 8 / 1e6)
        except:
            break
    return values

def plt_rx():
    host = pick_host_name(0)
    fname = os.path.join(args.dir, host, "net.txt")
    num = int(host.replace('l',''))
    iface = PI_DEV.get(num, 'eth2')
    print host, iface
    aggr_rx = parse_rate(fname, iface, RX)
    plt.plot(aggr_rx, lw=2, label="Server RX")

def plt_tcp():
    for i in [1]:
        host = pick_host_name(i)
        fname = os.path.join(args.dir, host, "net.txt")
        num = int(host.replace('l',''))
        iface = PI_DEV.get(num, 'eth2')
        print host, iface
        aggr_rx = parse_rate(fname, iface, TX)
        plt.plot(aggr_rx, lw=2, label="TCP TX")

def plt_udp():
    sum_rx = []
    for i in xrange(2, args.n+2):
        host = pick_host_name(i)
        if host == "l10":
            continue
        fname = os.path.join(args.dir, host, "net.txt")
        num = int(host.replace('l',''))
        iface = PI_DEV.get(num, 'eth2')
        print host, num, iface
        aggr_rx = parse_rate(fname, iface, TX)
        plt.plot(aggr_rx, lw=2)
        if i == 2:
            sum_rx = aggr_rx
        else:
            print len(aggr_rx), len(sum_rx)
            sum_rx = map(lambda (a,b): a+b, zip(sum_rx, aggr_rx))
    plt.plot(sum_rx, lw=2, label="Agg UDP RX", color="red")

plt_rx()
plt_tcp()
plt_udp()
plt.ylim((0, 10000))
plt.xlim((0,80))
plt.grid()
plt.title("Tenant rates")
plt.xlabel("Time (s)")
plt.ylabel("Mbps")
plt.legend()

if args.out:
    plt.savefig(args.out)
else:
    plt.show()
