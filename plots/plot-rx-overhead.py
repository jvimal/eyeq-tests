import plot_defaults
from helper import *
import math

parser = argparse.ArgumentParser()

parser.add_argument('--cols',
                    help="Columns to include for CPU usage",
                    action="store",
                    default='user,sys,sirq,hirq',
                    dest="cols")

parser.add_argument('--maxy',
                    help="Max CPU on y-axis",
                    action="store",
                    default=100,
                    dest="maxy",
                    type=int)

parser.add_argument('-o',
                    help="Output file to save",
                    default=None,
                    dest="out")

parser.add_argument('--text',
                    help="Plot rate text on the graph",
                    default=False,
                    action="store_true",
                    dest="text")

parser.add_argument('--dirs',
                    help="Directories to read output from",
                    default=['.'],
                    nargs="+",
                    dest="dirs")

args = parser.parse_args()

rates = [1000, 3000, 6000, 9000]
nums = [1, 8, 16, 32, 64, 92]

def dir_param(rate, without=False, num=1):
    dir = "r%s-n%d" % (rate, num)
    if without:
        dir = "rx-without/" + dir
    else:
        dir = "rx-with/" + dir
    return dir

def yvalue(rate, without=False, num=1, cols="sirq", rootdir="."):
    dir = rootdir + "/" + dir_param(rate, without, num)
    data = parse_cpu_usage(os.path.join(dir, "cpu.txt"))
    data = transpose(data)
    data = map(lambda d: avg(d[10:]), data)
    # user, sys, hirq, sirq
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

def yvalue2(rate, without=False, num=1, rootdir="."):
    dir = rootdir + "/" + dir_param(rate, without, num)
    data = parse_rate_usage(os.path.join(dir, "net.txt"),
                            ifaces=["eth2"], dir="rx", divider=(1 << 20))
    data = avg(data["eth2"][30:])
    #perf = perf_summary(os.path.join(dir, "perf.txt"))
    print dir, data
    #pprint(perf)
    return data

colours = blue_colours + ['black']
bar_width=1
bar_group=len(nums)+1
cols = args.cols

def avg(l):
    return sum(l) * 1.0 /len(l)

def stdev(l):
    m = avg(l)
    dev = map(lambda x: (x - m)**2, l)
    return math.sqrt(avg(dev))

def plot_without(without=False):
    alpha = 1
    first = True
    for i, n in enumerate(nums):
        xs = []
        xlabels = []
        ys = []
        yerrs = []
        xindex = i
        for rate in rates:
            xindex += bar_group
            xs.append(xindex)
            xlabels.append("%sG" % (rate/1000))
            temp_ys = []
            for dir in args.dirs:
                print dir
                temp_ys.append(yvalue(rate, num=n, without=without, cols=cols, rootdir=dir))
            ys.append(avg(temp_ys))
            yerrs.append(stdev(temp_ys))
            #rate = yvalue2(rate, num=n, without=without, rootdir=args.dir)
            if without == False and args.text:
                plt.text(xindex, ys[-1] + 10,
                         '%.1fM' % rate, rotation='vertical')

        if without == False:
            plt.bar(xs, ys, bar_width, color=colours[0], alpha=alpha, hatch='*', yerr=yerrs, ecolor='purple')
        else:
            plt.bar(xs, ys, bar_width, color=colours[i], label="%d" % n, yerr=yerrs, ecolor="black")#, alpha=alpha)
        plt.xlabel("Rate")
        plt.ylabel("CPU %")
        plt.xticks(xs, xlabels)
        if without == True:
            plt.legend(loc="upper left")

    #plt.title("CPU %s usage @ diff number of VQs/TCP connections.." % cols)
    plt.ylim((0,args.maxy))
    plt.grid(True)
    return

# This negative variable naming is a pain, I know! ;)
plot_without(False)
plot_without(True)
if args.out:
    plt.savefig(args.out)
else:
    plt.show()
