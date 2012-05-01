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
import os

parser = argparse.ArgumentParser(description="Perfiso consistent TX/RX overhead.")

parser.add_argument('--rate',
                    dest="rate",
                    action="store",
                    help="Aggregate rate of VQ/TXC.",
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
                    help="Number of VMs/tenants.",
                    default=1)

parser.add_argument('-t',
                    dest="t",
                    action="store",
                    type=int,
                    help="Time to run expt in seconds.",
                    default=120)

parser.add_argument('--enable',
                    dest="enable",
                    action="store_true",
                    default=False,
                    help="Enable eyeq")

parser.add_argument('--mtu',
                    dest="mtu",
                    help="Set MTU on hosts",
                    default="1500")

parser.add_argument('--vqupdate',
                    dest="vqupdate",
                    help="vqupdate interval",
                    default="25")

parser.add_argument('--datapath',
                    dest="datapath",
                    help="Measure overhead of this datapath",
                    choices=["rx", "tx"],
                    default="rx")

parser.add_argument("--profile",
                    dest="profile",
                    help="Directory to store profile data.  Omit if you don't want to profile",
                    default=None)

args = parser.parse_args()

class RxOverhead(Expt):
    def start(self):
        dir = self.opts("dir")
        if not os.path.exists(dir):
            os.makedirs(dir)

        h1 = Host("10.0.1.1")
        h2 = Host("10.0.1.2")
        hlist = HostList(h1, h2)
        self.hlist = hlist
        n = self.opts("n")

        hlist.rmmod()
        hlist.remove_qdiscs()
        if self.opts("enable"):
            hlist.insmod()
        else:
            # Rate limit second host to just the aggregate rate
            h2.insmod()
            h2.perfiso_set("ISO_MAX_TX_RATE", self.opts("rate"))
            h2.perfiso_set("ISO_RFAIR_INITIAL", self.opts("rate"))

        h1.perfiso_set("ISO_VQ_DRAIN_RATE_MBPS", self.opts('rate'))
        h1.perfiso_set("ISO_VQ_UPDATE_INTERVAL_US", self.opts("vqupdate"))

        # Create all IP routes etc.
        for i in xrange(n):
            hlist.create_ip_tenant(i+1)
        hlist.setup_tenant_routes(self.opts("n"))
        h1.start_monitors(self.opts("dir"))

        # Start iperf server
        iperf = Iperf({'-p': 5001})
        self.procs.append(iperf.start_server(h1))
        sleep(1)

        # Start all iperf clients
        for i in xrange(n):
            parallel = 4
            iperf = Iperf({'-p': 5001,
                           '-P': parallel,
                           '-i': '1',
                           '-c': h1.get_tenant_ip(i+1),
                           'dir': os.path.join(self.opts("dir"), "iperf"),
                           '-t': self.opts('t')})
            self.procs.append(iperf.start_client(h2))

        if self.opts("profile"):
            self.h1 = h1
            h1.start_profile(dir=self.opts("profile"))

    def stop(self):
        if self.opts("profile"):
            self.h1.stop_profile(dir=self.opts("profile"))

        self.hlist.remove_tenants()
        self.hlist.killall()

class TxOverhead(Expt):
    def start(self):
        h1 = Host("10.0.1.1")
        h2 = Host("10.0.1.2")
        hlist = HostList(h1, h2)
        self.hlist = hlist
        n = self.opts('n')

        hlist.rmmod()
        hlist.remove_qdiscs()
        hlist.configure_rps()
        n = self.opts('n')

        if self.opts("enable"):
            h1.insmod()
            h1.perfiso_set("ISO_MAX_TX_RATE", self.opts("rate"))
            h1.perfiso_set("ISO_RFAIR_INITIAL", self.opts("rate"))
        else:
            # insert htb qdiscs in hierarchy
            dev = h1.get_10g_dev()
            ceil = '%sGbit' % (int(self.opts('rate')) / 1000)
            cmd = "tc qdisc add dev %s root handle 1: htb default 1000" % dev
            h1.cmd(cmd)

            for i in xrange(n):
                classid = 10+i
                tip = h1.get_tenant_ip(i+1)
                rate = "%.3f" % (float(self.opts("rate")) / n)
                cmd = "tc class add dev %s parent 1: classid 1:%s " % (dev, classid)
                cmd += "htb rate %sMbit ceil %s mtu 64000"  % (rate, ceil)
                h1.cmd(cmd)

                cmd = 'tc filter add dev %s protocol ip parent 1: prio 1 ' % dev
                cmd += " u32 match ip src %s flowid 1:%s " % (tip, classid)
                h1.cmd(cmd)

        for i in xrange(n):
            #hlist.create_ip_tenant(i+1)
            ip = h1.get_tenant_ip(i+1)
            h1.perfiso_create_txc(ip)
            h1.tenants.append(i+1)
            h1.cmd("ifconfig %s:%d %s" % (h1.get_10g_dev(), i+1, ip))
            h2.cmd("ifconfig %s:%d %s" % (h2.get_10g_dev(), i+1, h2.get_tenant_ip(i+1)))
        hlist.setup_tenant_routes(n)
        h1.start_monitors(self.opts("dir"))

        # Start iperf server
        iperf = Iperf({'-p': 5001})
        self.procs.append(iperf.start_server(h2))
        sleep(1)

        # Start all iperf clients
        for i in xrange(n):
            parallel = 4
            iperf = Iperf({'-p': 5001,
                           '-P': parallel,
                           '-i': '1',
                           '-c': h2.get_tenant_ip(i+1),
                           'dir': os.path.join(self.opts("dir"), "iperf"),
                           '-t': self.opts('t')})
            self.procs.append(iperf.start_client(h1))
        if self.opts("profile"):
            self.h1 = h1
            h1.start_profile(dir=self.opts("profile"))
        return

    def stop(self):
        if self.opts("profile"):
            self.h1.stop_profile(dir=self.opts("profile"))

        self.hlist.remove_tenants()
        self.hlist.killall()
        self.hlist.remove_qdiscs()

if __name__ == "__main__":
    if args.datapath == "rx":
        RxOverhead(vars(args)).run()
    else:
        TxOverhead(vars(args)).run()
