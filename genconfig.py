from host import *
import argparse
from time import sleep
import subprocess

parser = argparse.ArgumentParser("Generate traffic pattern configs for Siva's loadgen program.")

parser.add_argument('--time',
                    dest="time",
                    default="60")

parser.add_argument('--port',
                    dest="port",
                    default="12345")

parser.add_argument('--type',
                    dest="type",
                    default="tcp",
                    choices=["tcp", "udp", "rpc"])

parser.add_argument('-n',
                    dest="n",
                    type=int,
                    help="Number of hosts",
                    default=4)

parser.add_argument('-P',
                    dest="P",
                    type=int,
                    help="Number of parallel connections per host",
                    default=1)

parser.add_argument('--traffic',
                    dest="traffic",
                    choices=["fullmesh", "incast", "sort", "hotspot"],
                    default="incast")

parser.add_argument('--pattern',
                    dest="pattern",
                    choices=["onoff", "longlived"],
                    default="onoff")

parser.add_argument('--size',
                    dest="size",
                    default="100M")

parser.add_argument('--duration',
                    dest="duration",
                    help="Duration: Flow lasts till size runs out/duration expires.",
                    default="86400s")

parser.add_argument('--on-off',
                    dest="on_off",
                    help="duration,inter specified together",
                    default=None)

parser.add_argument('--tenant',
                    dest="tenant",
                    type=int,
                    default=None)

parser.add_argument('--repeat',
                    dest="repeat",
                    type=int,
                    default=1000)

parser.add_argument('--inter',
                    dest="inter",
                    default="10s")

parser.add_argument('--start',
                    dest="start",
                    default="20.0")

args = parser.parse_args()
if args.on_off:
    try:
        args.duration, args.inter = args.on_off.split(',')
    except:
        pass

def parse_size(s):
    if 'K' in s:
        size = int(s.replace('K','')) * 10**3
    elif 'M' in s:
        size = int(s.replace('M', '')) * 10**6
    elif 'G' in s:
        size = int(s.replace('G', '')) * 10**9
    elif 'T' in s:
        size = int(s.replace('T', '')) * 10**12
    else:
        size = int(s)
    return size

def parse_duration(s):
    d = 1e6
    if 'us' in s:
        d = float(s.replace('us', '')) * 1e-6
    elif 'ms' in s:
        d = float(s.replace('ms', '')) * 1e-3
    elif 's' in s:
        d = float(s.replace('s', '')) * 1
    else:
        d = float(s)
    return d

# Simple full mesh
def fullmesh(sort=False):
    n = args.n
    type = args.type.upper()
    time = args.time
    port = args.port
    seed = 0
    P = args.P
    size = parse_size(args.size)
    start = args.start
    duration = parse_duration(args.duration)
    inter = parse_duration(args.inter)
    repeat = args.repeat

    if args.repeat == -1:
        repeat = 10**15

    if sort:
        # 1 day
        time = 86400
        pairs = n * (n-1)
        # Size is interpreted as total size of data to sort
        size_per_flow = size / (pairs * P)
        size = size_per_flow
        repeat = 1

    print "#src_ip dst_ip dst_port type seed start_time stop_time flow_size r/e repetitions time_between_flows r/e (rpc_delay r/e)"

    for i in xrange(n):
        hi = pick_10g_ip(i)
        if args.tenant:
            hi = Host(pick_host_ip(i)).get_tenant_ip(args.tenant)
        for j in xrange(n):
            if i == j:
                continue
            for p in xrange(P):
                seed += 1
                hj = pick_10g_ip(j)
                if args.tenant:
                    hj = Host(pick_host_ip(j)).get_tenant_ip(args.tenant)
                out = "%s %s " % (hi, hj)
                out += "%s %s %s " % (port, type, seed)
                out += "%s %s " % (start, time)
                out += "%s exact " % size
                out += "%s %.6f exact " % (repeat, inter)
                out += "%.6f " % duration
                print out

def nto1():
    n = args.n
    type = args.type.upper()
    time = args.time
    port = args.port
    seed = 0
    size = parse_size(args.size)
    duration = parse_duration(args.duration)
    P = args.P
    start = args.start
    inter = parse_duration(args.inter)
    repeat = args.repeat

    if repeat == -1:
        repeat = 10**15

    print "#src_ip dst_ip dst_port type seed start_time stop_time flow_size r/e repetitions time_between_flows r/e (rpc_delay r/e)"

    h0 = pick_10g_ip(0)
    if args.tenant:
        h0 = Host(pick_host_ip(0)).get_tenant_ip(args.tenant)
    for i in xrange(2,n):
        hi = pick_10g_ip(i)
        if args.tenant:
            hi = Host(pick_host_ip(i)).get_tenant_ip(args.tenant)
        for p in xrange(P):
            seed += 1
            out = "%s %s " % (hi, h0)
            out += "%s %s %s " % (port, type, seed)
            out += "%s %s " % (start, time)
            out += "%s exact " % size
            out += "%s %.6f exact " % (repeat, inter)
            out += "%.6f " % duration
            print out

def hotspot():
    n = args.n
    type = args.type.upper()
    time = args.time
    port = args.port
    seed = 0
    size = parse_size(args.size)
    P = args.P
    start = args.start
    inter = parse_duration(args.inter)
    duration = parse_duration(args.duration)
    repeat = args.repeat
    if repeat == -1:
        repeat = 10**15

    print "#src_ip dst_ip dst_port type seed start_time stop_time flow_size r/e repetitions time_between_flows r/e (rpc_delay r/e)"

    for i in xrange(n):
        # all send to host i
        hi = pick_10g_ip(i)
        if args.tenant:
            hi = Host(pick_host_ip(i)).get_tenant_ip(args.tenant)
        start = i * 4
        for j in xrange(n):
            if i == j:
                continue
            seed += 1
            hj = pick_10g_ip(j)
            if args.tenant:
                hj = Host(pick_host_ip(j)).get_tenant_ip(args.tenant)
            out = "%s %s " % (hj, hi)
            out += "%s %s %s " % (port, type, seed)
            out += "%s %s " % (start, time)
            out += "%s exact " % size
            out += "%s %.6f exact " % (repeat, inter)
            out += "%.6f " % duration
            print out
    return

if args.traffic == "fullmesh":
    fullmesh()
elif args.traffic == "incast":
    nto1()
elif args.traffic == "sort":
    fullmesh(sort=True)
elif args.traffic == "hotspot":
    hotspot()
