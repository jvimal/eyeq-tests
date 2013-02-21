#!/usr/bin/python

from mininet.topo import Topo
from mininet import node
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import lg
from mininet.link import TCLink

from subprocess import Popen, PIPE
from time import sleep, time
import multiprocessing
import termcolor as T
import argparse
import random
import sys
import os

parser = argparse.ArgumentParser(description="EyeQ test topology in Mininet")
parser.add_argument('--num-hosts',
                    type=int,
                    default=4)
parser.add_argument('--num-tenants',
                    type=int,
                    help="Number of tenants in every host",
                    default=3)
args = parser.parse_args()

lg.setLogLevel('info')

def cmd(h, c, **kwargs):
    if not kwargs.get("quiet", False):
        print c
    h.sendCmd(c)
    h.waitOutput()

def rootcmd(c, **kwargs):
    if not kwargs.get("quiet", False):
        print c
    Popen(c, shell=True).wait()

class StarTopo(Topo):
    def __init__(self, n=3):
        super(StarTopo, self).__init__()
        hosts = []
        for i in xrange(n):
            name = 'h%d' % (i + 1)
            host = self.addHost(name)
            hosts.append(host)
        switch = self.addSwitch('s0')
        for h in hosts:
            self.addLink(h, switch)
        return

def ssh_init(net):
    lg.info("--- Starting sshd inside all hosts\n")
    for host in net.hosts:
        cmd(host, "/usr/sbin/sshd", quiet=True)
    return

def eyeq_conf(net):
    dir = os.path.dirname(os.path.abspath(__file__)) + "/"
    basedir = dir + "../../"
    testdir = dir + "../"

    lg.info("--- Please wait while we create+configure tenants through ssh.\n")
    lg.info("    This can take a while...\n")
    h1 = net.get("h1")
    cmd(h1, "python %s/tenant.py -m %d -T %d" % (testdir, args.num_hosts, args.num_tenants))

    lg.info("\n--- Setting parameters for 100Mb/s\n")
    rootcmd("bash %s/100mbps.sh %s" % (dir, basedir))

def set_switch_rates(net):
    lg.info("--- Adding rate limits to switches.\n")
    for sw in net.switches:
        for intf in sw.intfs.itervalues():
            dev = intf.name
            if dev == "lo":
                continue
            c = "tc qdisc add dev %s root handle 1: tbf limit 150000 burst 15000 rate 100Mbit" % dev
            rootcmd(c)
    return

def main():
    topo = StarTopo(n=args.num_hosts)
    net = Mininet(topo=topo)
    net.start()
    ssh_init(net)
    eyeq_conf(net)
    set_switch_rates(net)
    CLI(net)
    net.stop()
    return

main()

