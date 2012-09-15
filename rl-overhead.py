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

parser = argparse.ArgumentParser(description="RL overhead.")

parser.add_argument('--rate',
                    dest="rate",
                    action="store",
                    help="Aggregate rate of RL.",
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

parser.add_argument('--rl',
                    dest="rl",
                    choices=["newrl", "htb"],
                    help="Choose rate limiter")

parser.add_argument("--profile",
                    dest="profile",
                    help="Directory to store profile data.  Omit if you don't want to profile",
                    default=None)

args = parser.parse_args()

class RlOverhead(Expt):
    def start(self):
        h1 = Host("10.0.1.1")
        h2 = Host("10.0.1.2")
        hlist = HostList(h1, h2)
        self.hlist = hlist
        n = self.opts('n')

        hlist.cmd("rmmod newrl")
        hlist.remove_qdiscs()
        hlist.configure_rps()
        n = self.opts('n')

        if self.opts("rl") == "newrl":
            dev = h1.get_10g_dev()
            rate = self.opts("rate")
            h1.cmd("insmod ~/vimal/exports/newrl.ko rate=%s dev=%s" % (rate, dev))
        else:
            # insert htb qdiscs in hierarchy
            dev = h1.get_10g_dev()
            ceil = '%sGbit' % (int(self.opts('rate')) / 1000)
            cmd = "tc qdisc add dev %s root handle 1: htb default 1000" % dev
            h1.cmd(cmd)

        # Start iperf server
        iperf = Iperf({'-p': 5001})
        self.procs.append(iperf.start_server(h2))
        sleep(1)

        # Start all iperf clients
        iperf = Iperf({'-p': 5001,
                       '-P': n * 2,
                       '-i': '10',
                       '-c': h2.get_10g_ip(),
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

        self.hlist.killall()
        self.hlist.remove_qdiscs()
        self.hlist.cmd("rmmod newrl")

if __name__ == "__main__":
    RlOverhead(vars(args)).run()
