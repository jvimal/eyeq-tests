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

parser.add_argument('--dir',
                    dest="dir",
                    required=True)

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

scen = Scenarios()
scen.add("tcp2vs32", Tcp2Vs32(t=args.time, enabled=args.enabled))
scen.add("tcpvsudp", TcpVsUdp(t=240, enabled=args.enabled))

if args.list:
    scen.list()
if args.run:
    scen.run(args.run)
