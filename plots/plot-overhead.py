import plot_defaults
from helper import *
import math

parser = argparse.ArgumentParser()

rates = [1000, 3000, 6000, 9000]
nums = [1, 16, 32, 64]

parser.add_argument('--cols',
                    help="Columns to include for CPU usage",
                    action="store",
                    default='user,sys,sirq,hirq',
                    dest="cols")

parser.add_argument('--maxy',
                    help="Max CPU on y-axis",
                    action="store",
                    default=8,
                    dest="maxy",
                    type=int)

parser.add_argument('-o', '--out',
                    help="Output file to save",
                    default=None,
                    dest="out")

parser.add_argument('--dir',
                    help="old option (deprecated)",
                    default='.',
                    dest="dir")

parser.add_argument('--dirs',
                    help="Directories to read output from",
                    default=[],
                    nargs="+",
                    dest="dirs")

parser.add_argument('--dp',
                    help="Datapath",
                    choices=["tx", "rx"],
                    default="tx",
                    dest="dp")

parser.add_argument('--test',
                    default=False,
                    dest="test",
                    action="store_true")

# For testing
parser.add_argument('-n', dest='n')
parser.add_argument('-C', dest='C')
parser.add_argument('--enable', dest='enable', action="store_true")

args = parser.parse_args()
#args.dir = os.path.join(args.dir, args.dp)

def dir_param(n, C, enable):
    return "n%s-C%s-iso%s" % (n, C, ("--enable" if enable else ""))

def yvalue_cpu(n, C, enable, cols):
    dir = dir_param(n, C, enable)
    data = parse_cpu_usage(os.path.join(args.dir, dir, "cpu.txt"))
    data = transpose(data)
    data = map(lambda d: avg(d[10:-10]), data)
    data = {
        'user': data[0],
        'sys': data[1],
        'hirq': data[4],
        'sirq': data[5]
        }
    ret = 0.0
    for col in cols.split(','):
        ret += data[col]
    return ret

def yvalue_net(n, C, enable, dp):
    dir = dir_param(n, C, enable)
    data = parse_rate_usage(os.path.join(args.dir, dir, "net.txt"),
                            ifaces=["eth2"], dir=dp, divider=(1 << 20))
    try:
        data = avg(data["eth2"][10:])
    except:
        data = 0
    return data

def plot():
    N = len(nums)
    L = len(rates)
    blue_colours.append('black')
    half = N/2.0 + (L+1) * np.arange(0, N)
    xlabels = ['%dG' % (rate/1000) for rate in rates]
    dirs = list(args.dirs)

    plot_defaults.rcParams['figure.figsize'] = 10, 3.5

    for i,n in enumerate(nums):
        print '---'
        ys = []

        for C in rates:
            cpus_with = []
            cpus_without = []

            for dir in dirs:
                args.dir = os.path.join(dir, args.dp)
                cpu_with = yvalue_cpu(n, C, True, args.cols)
                cpu_without = yvalue_cpu(n, C, False, args.cols)

                cpus_with.append(cpu_with)
                cpus_without.append(cpu_without)
            #net_with = yvalue_net(n, C, True, args.dp)
            #net_without = yvalue_net(n, C, False, args.dp)

            ovhead = (avg(cpus_with) - avg(cpus_without))
            ys.append(ovhead)
            print n, C, ovhead, '%.3f - %.3f' % (avg(cpus_with), avg(cpus_without))
        xs = i + (L+1) * np.arange(0, N)

        plt.bar(xs, ys, color=blue_colours[i], label='$n=%d$' % n, width=1)
    plt.ylim((0, args.maxy))
    plt.xticks(half, xlabels)
    plt.yticks(np.arange(0, 6.1, 2))
    plt.ylabel("CPU overhead (%)")
    plt.legend(loc="upper left")

def test():
    n = args.n
    C = args.C
    dir = dir_param(n, C, args.enable)
    print "%s %.3f" % (dir, yvalue_cpu(n, C, args.enable, args.cols))

if args.out:
    plot()
    plt.savefig(args.out)
elif args.test:
    test()
else:
    plot()
    plt.show()
