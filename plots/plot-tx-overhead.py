import plot_defaults
from helper import *

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('-o', '--out',
                    dest="out",
                    default=None)

parser.add_argument('-p',
                    dest="plot",
                    choices=["number","rate", "conn"],
                    default="number")

args = parser.parse_args()

rates = [1000, 3000, 6000, 9000]
rls = ['htb', 'perfiso']
num = 64
rates = [100]
timeout=500*1000

def dir_param(rl, rate, num=None, timeout=None):
    if rl == "htb":
        timeout=500*1000
    if timeout is not None:
        dir = "rl%s-r%s-tmout%d" % (rl, rate, timeout)
    if num is not None and timeout is not None:
        dir = "rl%s-r%s-n%d-tmout%d" % (rl, rate, num, timeout)
    if timeout is None:
        dir = "rl%s-r%s-n%d-tmout" % (rl, rate, num)
    return dir

def yvalue2(rl, rate, num=None, timeout=None):
    dir = dir_param(rl, rate, num, timeout)
    data = parse_rate_usage(os.path.join(dir, "net.txt"),
                            ifaces=["eth2"], dir="tx", divider=1e6)
    data = avg(data["eth2"][30:])
    #perf = perf_summary(os.path.join(dir, "perf.txt"))
    #pprint(perf)
    return data

def yvalue(rl, rate, num=None, timeout=None, cols="sirq"):
    dir = dir_param(rl, rate, num, timeout)
    data = parse_cpu_usage(os.path.join(dir, "cpu.txt"))
    data = transpose(data)
    data = map(lambda d: avg(d[10:]), data)
    print dir, yvalue2(rl, rate, num, timeout)
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

def yvalue_P(rl, P=4, cols="sirq"):
    dir = "rl%s-r9000-P%d" % (rl, P)
    data = parse_cpu_usage(os.path.join(dir, "cpu.txt"))
    data = transpose(data)
    data = map(lambda d: avg(d[10:]), data)
    print dir
    data = {
        'user': data[0],
        'sys': data[1],
        'hirq': data[4],
        'sirq': data[5]
        }
    ret = 0.0
    for col in cols.split(','):
        ret += data[col]
    data = parse_rate_usage(os.path.join(dir, "net.txt"),
                            ifaces=["eth2"], dir="tx", divider=1e6)
    data = avg(data["eth2"][30:])
    print yvalue2_P(rl, P)
    return ret

def yvalue2_P(rl, P=4):
    dir = "rl%s-r9000-P%d" % (rl, P)
    data = parse_rate_usage(os.path.join(dir, "net.txt"),
                            ifaces=["eth2"], dir="tx", divider=1e6)
    data = avg(data["eth2"][30:])
    return data

bar_width=1
bar_group=3
colours = blue_colours

def get_hatch(rl):
    if rl == "perfiso":
        return '*'
    return ' '

def get_label(rl):
    if rl == "perfiso":
        return 'EyeQ'
    return rl

def vary_number(timeout=None):
    rate = 100
    xlabels = []
    fig = plt.figure()
    for i, rl in enumerate(rls):
        xs = []
        ys = []
        xlabels = []
        for index, num in enumerate([8, 16, 32, 64, 128]):
            xs.append(3*index + i)
            ys.append(yvalue(rl, rate, num, timeout=timeout, cols="user,sirq,sys,hirq"))
            #plt.text(3*index+i, 10,
            #         '%.1fM' % yvalue2(rl, rate, num, timeout),
            #         rotation='vertical',
            #         fontsize=24)
            xlabels.append(str(num))
        plt.bar(xs, ys, bar_width, label=get_label(rl), color=colours[i], hatch=get_hatch(rl))
        plt.xticks(xs, xlabels)
        plt.ylabel("CPU %")
        plt.xlabel("Number of RLs")
    plt.grid(True)
    plt.legend(loc="upper left")
    #plt.title("Vary # RLs for rate=100Mbps")
    plt.ylim((0,15))
    return

def vary_rate(timeout=timeout):
    rates = [1000, 3000, 6000, 9000]
    fig = plt.figure()
    for i, rl in enumerate(rls):
        xs = []
        ys = []
        xlabels = []
        for index, rate in enumerate(rates):
            xs.append(3*index + i)
            xlabels.append("%sG" % (rate/1000))
            ys.append(yvalue(rl, rate, timeout=timeout, cols="user,sirq,sys,hirq"))
            plt.text(3*index+i, 10,
                     '%.1fM' % yvalue2(rl, rate, timeout=timeout),
                     rotation='vertical',
                     fontsize=24)

        plt.bar(xs, ys, bar_width, label=get_label(rl), color=colours[i], hatch=get_hatch(rl))
        plt.xlabel("Rate")
        plt.ylabel("CPU %")
        plt.xticks(xs, xlabels)
    plt.grid(True)
    plt.legend(loc="upper left")
    #plt.title("Vary rates for different RLs for perfiso")
    plt.ylim((0,15))
    return

def vary_connections():
    rates = [9000]
    Ps = [4, 16, 32, 64, 128]
    fig = plt.figure()
    bar_width = 1
    for i, rl in enumerate(rls):
        xs = []
        ys = []
        xlabels = []
        for index, P in enumerate(Ps):
            xs.append(3*index + i)
            xlabels.append(str(P))
            ys.append(yvalue_P(rl, P, cols="user,sirq,sys,hirq"))
            plt.text(3*index+i, 20,
                     '%.1fM' % yvalue2_P(rl, P),
                     rotation='vertical',
                     fontsize=24)

        plt.bar(xs, ys, bar_width, label=get_label(rl), color=colours[i], hatch=get_hatch(rl))
        plt.xlabel("Num TCP connections")
        plt.ylabel("CPU %")
        plt.xticks(xs, xlabels)
    plt.grid(True)
    plt.legend(loc="upper left")
    #plt.title("CPU usage, parallel iperf sessions, bound to diff CPUs")
    plt.ylim((0,30))
    return

if args.plot == "number":
    try:
        vary_number(timeout=timeout)
    except:
        vary_number()
elif args.plot == "rate":
    vary_rate()
elif args.plot == "conn":
#vary_rate(timeout=timeout)
    vary_connections()
if args.out:
    plt.savefig(args.out)
else:
    plt.show()
