from helper import *

parser = argparse.ArgumentParser()

parser.add_argument('--cols',
                    help="Columns to include for CPU usage",
                    action="store",
                    default='sirq,hirq',
                    dest="cols")

parser.add_argument('--maxy',
                    help="Max CPU on y-axis",
                    action="store",
                    default=100,
                    dest="maxy",
                    type=int)

args = parser.parse_args()

rates = [1000, 3000, 6000, 9000]
nums = [1, 8, 16, 32, 64, 128]

def dir_param(rate, without=False, num=1):
    dir = "r%s-n%d" % (rate, num)
    if without:
        dir = "rx-without/" + dir
    else:
        dir = "rx-with/" + dir
    return dir

def yvalue(rate, without=False, num=1, cols="sirq"):
    dir = dir_param(rate, without, num)
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

def yvalue2(rate, without=False, num=1):
    dir = dir_param(rate, without, num)
    data = parse_rate_usage(os.path.join(dir, "net.txt"),
                            ifaces=["eth2"], dir="rx", divider=(1 << 20))
    data = avg(data["eth2"][30:])
    perf = perf_summary(os.path.join(dir, "perf.txt"))
    print dir, data
    #pprint(perf)
    return data

colours = default_colours
bar_width=1
bar_group=len(nums)+1
cols = args.cols

def plot_without(without=False):
    alpha = 0.3
    first = True
    for i, n in enumerate(nums):
        xs = []
        xlabels = []
        ys = []
        xindex = i
        for rate in rates:
            xindex += bar_group
            xs.append(xindex)
            xlabels.append("%sG" % (rate/1000))
            ys.append(yvalue(rate, num=n, without=without, cols=cols))
            yvalue2(rate, num=n, without=without)

        if without == False:
            plt.bar(xs, ys, bar_width, color=colours[i], alpha=alpha)
        else:
            plt.bar(xs, ys, bar_width, color=colours[i], label="4x%d" % n)
        plt.xlabel("Rate")
        plt.ylabel("CPU usage fraction")
        plt.xticks(xs, xlabels)
        if without == True:
            plt.legend(loc="upper left")

    plt.title("CPU %s usage @ diff number of VQs/TCP connections.." % cols)
    plt.ylim((0,args.maxy))
    plt.grid(True)
    return

# This negative variable naming is a pain, I know! ;)
plot_without(False)
plot_without(True)
plt.show()
