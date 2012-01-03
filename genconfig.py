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

args = parser.parse_args()

# Simple full mesh
def fullmesh():
    n = args.n
    type = args.type.upper()
    time = args.time
    port = args.port
    seed = 0
    P = args.P

    print "#src_ip dst_ip dst_port type seed start_time stop_time flow_size r/e repetitions time_between_flows r/e (rpc_delay r/e)"

    for i in xrange(n):
        hi = pick_10g_ip(i)
        for j in xrange(n):
            if i == j:
                continue
            for p in xrange(P):
                seed += 1
                hj = pick_10g_ip(j)
                out = "%s %s " % (hi, hj)
                out += "%s %s %s " % (port, type, seed)
                out += "%s %s " % (0.0, time)
                out += "1000000000000 random "
                out += "1000 0.001 random"
                print out

def nto1():
    n = args.n
    type = args.type.upper()
    time = args.time
    port = args.port
    seed = 0
    P = args.P
    print "#src_ip dst_ip dst_port type seed start_time stop_time flow_size r/e repetitions time_between_flows r/e (rpc_delay r/e)"

    h0 = pick_10g_ip(0)
    for i in xrange(1,n):
        hi = pick_10g_ip(i)
        for p in xrange(P):
            seed += 1
            out = "%s %s " % (hi, h0)
            out += "%s %s %s " % (port, type, seed)
            out += "%s %s " % (0.0, time)
            out += "100000000 random "
            out += "1000 10 random"
            print out

fullmesh()
#nto1()
