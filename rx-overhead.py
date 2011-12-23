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

sys.path = ['/root/vimal/10g/perfiso_10g_linux/tools'] + sys.path
import perfiso

parser = argparse.ArgumentParser(description="Perfiso RX overhead test.")
parser.add_argument('--rate',
                    dest="rate",
                    action="store",
                    help="Rate of VQ.",
                    required=True)

parser.add_argument('--dir',
                    dest="dir",
                    action="store",
                    help="Directory to store outputs.",
                    required=True)

parser.add_argument('-n',
                    dest="n",
                    action="store",
                    type=int,
                    help="Number of VQs.",
                    default=1)

parser.add_argument('-t',
                    dest="t",
                    action="store",
                    type=int,
                    help="Time to run expt in seconds.",
                    default=120)

parser.add_argument('--timeout',
                    dest="timeout",
                    action="store",
                    help="Timeout for VQ updates (in microseconds).",
                    default=str(100))

parser.add_argument('--without-vq',
                    dest="without_vq",
                    action="store_true",
                    help="Do expt without VQ",
                    default=False)

parser.add_argument("--profile",
                    dest="profile",
                    help="Directory to store profile data.  Omit if you don't want to profile",
                    default=None)

args = parser.parse_args()

if int(args.timeout) <= 10:
    print "Too low timeout, but nothing prevents you from setting it."
    sys.exit(0)

class RxOverhead(Expt):
    def start(self):
        h1 = Host("10.0.1.1")
        h2 = Host("10.0.1.2")
        hlist = HostList(h1, h2)
        self.hlist = hlist
        n = self.opts('n')

        hlist.rmmod()
        hlist.remove_qdiscs()
        hlist.insmod()

        hlist.prepare_iface()
        # VQ drain rate
        h1.perfiso_set("ISO_VQ_DRAIN_RATE_MBPS", self.opts('rate'))

        # Create vq class
        self.log("Creating vq classes")
        for i in xrange(n):
            hlist.create_ip_tenant(i+1)

        h1.start_monitors(self.opts('dir'))

        self.log("Starting %d iperfs" % n)
        # Start iperfs servers
        for i in xrange(n):
            parallel = 4
            iperf = Iperf({'-p': 5001,
                           '-P': parallel})
            server = iperf.start_server(h1)
            self.procs.append(server)
            self.log("server %d" % i)

        sleep(1)
        for i in xrange(n):
            iperf = Iperf({'-p': 5001,
                           '-P': parallel,
                           '-c': h1.get_tenant_ip(i+1),
                           '-t': self.opts('t')})
            client = iperf.start_client(h2)
            self.procs.append(client)
            self.log("client %d" % i)
        if self.opts("profile"):
            h1.start_profile(dir=self.opts("profile"))
        self.h1 = h1

    def stop(self):
        if self.opts("profile"):
            self.h1.stop_profile(dir=self.opts("profile"))
        self.hlist.killall()
        self.hlist.remove_tenants()
        for p in self.procs:
            p.kill()

class RxOverhead2(Expt):
    def start(self):
        h1 = Host("10.0.1.1")
        h2 = Host("10.0.1.2")
        hlist = HostList(h1, h2)
        self.hlist = hlist
        n = self.opts('n')

        hlist.rmmod()
        hlist.remove_qdiscs()
        n = self.opts('n')

        hlist.prepare_iface()

        # Insert the module only in the second host
        h2.insmod()
        h2.perfiso_set("ISO_MAX_TX_RATE", self.opts("rate"))
        h2.perfiso_set("ISO_RFAIR_INITIAL", self.opts('rate'))

        # Create vq class
        # First host doesn't have module loaded
        ip = h2.get_10g_ip()
        h2.perfiso_create_txc(ip)

        h1.start_monitors(self.opts('dir'))
        if not self.opts("profile"):
            h1.start_perf_monitor(self.opts("dir"), self.opts('t'))

        self.log("Starting %d iperfs" % n)
        # Start same number of iperf servers
        for i in xrange(n):
            parallel = 4
            iperf = Iperf({'-p': 5001,
                           '-P': parallel})
            server = iperf.start_server(h1)
            self.procs.append(server)

        sleep(1)
        for i in xrange(n):
            iperf = Iperf({'-p': 5001,
                           '-P': parallel,
                           '-c': h1.get_10g_ip(),
                           '-t': self.opts('t')})
            client = iperf.start_client(h2)
            self.procs.append(client)

    def stop(self):
        self.hlist.remove_tenants()
        self.hlist.killall()
        for p in self.procs:
            p.kill()

if not args.without_vq:
    RxOverhead({
            'n': args.n,
            'dir': args.dir,
            'rate': args.rate,
            't': args.t,
            'timeout': args.timeout,
            'profile': args.profile,
            }).run()
else:
    RxOverhead2({
            'n': args.n,
            'dir': args.dir,
            'rate': args.rate,
            't': args.t,
            'timeout': args.timeout,
            'profile': args.profile,
            }).run()
