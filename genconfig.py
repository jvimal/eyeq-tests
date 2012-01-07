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
                    default=4)

parser.add_argument('--traffic',
                    dest="traffic",
                    choices=["fullmesh", "incast"],
                    default="incast")

parser.add_argument('--pattern',
                    dest="pattern",
                    choices=["onoff", "longlived"],
                    default="onoff")

parser.add_argument('--size',
                    dest="size",
                    default="100M")

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
                    type=int,
                    default=10)


args = parser.parse_args()

def parse_size(s):
    if 'K' in s:
        size = int(s.replace('K','')) * 10**3
    if 'M' in s:
        size = int(s.replace('M', '')) * 10**6
    elif 'G' in s:
        size = int(s.replace('G', '')) * 10**9
    return size

# Simple full mesh
def fullmesh():
    n = args.n
    type = args.type.upper()
    time = args.time
    port = args.port
    seed = 0
    P = args.P
    size = parse_size(args.size)

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
                out += "%s %s " % (0.0, time)
                out += "%s exact " % size
                out += "%s %s exact" % (args.repeat, args.inter)
                print out

def nto1():
    n = args.n
    type = args.type.upper()
    time = args.time
    port = args.port
    seed = 0
    size = parse_size(args.size)
    P = args.P
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
            out += "%s %s " % (0.0, time)
            out += "%s exact " % size
            out += "%s %s exact" % (args.repeat, args.inter)
            print out

if args.traffic == "fullmesh":
    fullmesh()
elif args.traffic == "incast":
    nto1()
