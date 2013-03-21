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

parser = argparse.ArgumentParser(description="Create tenants on few machines.")
parser.add_argument('-T',
                    type=int,
                    help="Number of tenants.",
                    default=1)

parser.add_argument('-m',
                    type=int,
                    help="Number of machines.",
                    default=2)

parser.add_argument('--mtu',
                    dest="mtu",
                    help="MTU of 10G interface",
                    default='1500')

parser.add_argument('--remove',
                    help="Remove module/tenants.",
                    action="store_true",
                    default=False)

parser.add_argument('--rate',
                    dest="rate",
                    help="max VQ/TX rate",
                    default="9000")

args = parser.parse_args()

class Tenants(Expt):
    def initialise(self):
        self.hlist.rmmod()
        self.hlist.remove_qdiscs()
        self.hlist.insmod()

    def prepare_iface(self):
        h = self.hlist
        h.set_mtu(self.opts("mtu"))

        h.prepare_iface()
        for tid in xrange(self.opts("T")):
            h.create_ip_tenant(tid+1)
        h.setup_tenant_routes(self.opts("T"))

    def start(self):
        hlist = HostList()
        for i in xrange(self.opts("m")):
            ip = pick_host_ip(i)
            h = Host(ip)
            h.id = i + 1
            hlist.append(h)
            self.log(T.colored(ip, "green"))
        self.hlist = hlist
        if self.opts("remove"):
            self.stop()
            sys.exit(0)
        self.initialise()
        hlist.perfiso_set("ISO_VQ_DRAIN_RATE_MBPS", self.opts("rate"))
        hlist.perfiso_set("ISO_MAX_TX_RATE", self.opts("rate"))
        self.prepare_iface()
        sys.exit(0)

    def stop(self):
        self.hlist.remove_tenants()
        self.hlist.rmmod()

Tenants(vars(args)).run()
