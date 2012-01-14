#!/usr/bin/python
import sys
import argparse
import multiprocessing
from common import *
import termcolor as T
from expt import Expt
from iperf import Iperf
from time import sleep
from host import *

parser = argparse.ArgumentParser(description="Perfiso simple scenarios testing.")
parser.add_argument('--run',
                    dest="run",
                    default=None,
                    help="Test name to run.")

parser.add_argument('--list', '-l',
                    dest="list",
                    action="store_true",
                    default=False)

parser.add_argument('-P', '--nflows',
                    dest="P",
                    action="store",
                    type=int,
                    default=4)

parser.add_argument('-n',
                    dest="n",
                    action="store",
                    type=int,
                    default=1)

parser.add_argument('--dir',
                    dest="dir",
                    default="/tmp")

parser.add_argument('--enable',
                    action="store_true",
                    dest="enabled",
                    help="Enable perfisolation",
                    default=False)

parser.add_argument('--time', '-t',
                    type=int,
                    dest="time",
                    help="Time to run expt",
                    default=120)

parser.add_argument('--wtcp',
                    dest="wtcp",
                    help="For the tcp vs udp test, weight of the TCP flow.",
                    default="1")

parser.add_argument('--case',
                    dest="case",
                    type=int,
                    help="For the memcached test, select case to run.",
                    default=1)

parser.add_argument('--start-udp',
                    dest="start_udp",
                    help="For the UDP tests, select time to start UDP flow")

parser.add_argument('--traffic',
                    dest="traffic",
                    action="store",
                    help="For the tcpvsudp test use the traffic matrix from this file")

parser.add_argument('--mtu',
                    dest="mtu",
                    help="MTU For the tcpvsudp test")

parser.add_argument('--vqupdate',
                    dest="vqupdate",
                    help="VQ update interval in us",
                    default="25")

parser.add_argument('--vqrate',
                    dest="vqrate",
                    help="VQ drain rate in Mbps",
                    default="8500")

args = parser.parse_args()

def indent(s, depth=1, char='\t'):
    lines = []
    for line in s.split("\n"):
        lines.append((char * depth + line))
    return '\n'.join(lines)

class Scenarios:
    def __init__(self):
        self.scenarios = {}

    def list(self):
        for name, scen in self.scenarios.iteritems():
            print name
            print indent(scen.desc)

    def add(self, name, scen):
        self.scenarios[name] = scen

    def run(self, name):
        scen = self.scenarios.get(name, None)
        if scen is not None:
            scen.run()
        else:
            print "Scenario %s not found!"

from test_tcp2vs32 import Tcp2Vs32
from test_tcpvsudp import TcpVsUdp
from test_udp import Udp
from test_memcached import Memcached

scen = Scenarios()
scen.add("tcp2vs32", Tcp2Vs32(t=args.time, enabled=args.enabled, dir=args.dir))
scen.add("tcpvsudp", TcpVsUdp(t=args.time, enabled=args.enabled,
                              P=args.P, n=args.n, dir=args.dir, wtcp=args.wtcp,
                              mtu=args.mtu, vqupdate=args.vqupdate,
                              vqrate=args.vqrate,
                              start_udp=args.start_udp, traffic=args.traffic))
scen.add("udp", Udp(t=args.time, enabled=args.enabled,
                    P=args.P, dir=args.dir, start_udp=args.start_udp))
scen.add("memcached", Memcached(t=args.time, dir=args.dir, case=args.case))

if args.list:
    scen.list()
if args.run:
    scen.run(args.run)
else:
    parser.print_help()
