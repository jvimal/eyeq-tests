#!/usr/bin/python

from mininet.topo import Topo
from mininet import node
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import lg
from mininet.link import TCLink
from mininet.util import dumpNodeConnections

from bridge import LinuxBridge
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
parser.add_argument('--conf',
                    action="store_true",
                    default=False)
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

class Dumbell(Topo):
    def __init__(self, n=3):
        """@n is the number of hosts on each side of the dumbell
        topo."""
        Topo.__init__(self)
        hosts = []
        for i in xrange(2 * n):
            name = 'h%d' % (i + 1)
            host = self.addHost(name)
            hosts.append(host)
        switch0 = self.addSwitch('s0')
        switch1 = self.addSwitch('s1')
        L = len(hosts)
        for h in hosts[0:L/2]:
            self.addLink(h, switch0)
        for h in hosts[L/2:]:
            self.addLink(h, switch1)
        self.addLink(switch0, switch1)

def ssh_init(net):
    lg.info("--- Starting sshd inside all hosts\n")
    for host in net.hosts:
        cmd(host, "/usr/sbin/sshd", quiet=True)
    return

def mem_init(net):
    lg.info("--- Starting memcached inside all hosts\n")
    for host in net.hosts:
        cmd(host, "/usr/bin/memcached -m 64 -p 11211 -u memcache -d")
    return

def getdir():
    return os.path.dirname(os.path.abspath(__file__)) + "/"

def eyeq_conf(net):
    dir = getdir()
    basedir = dir + "../../"
    testdir = dir + "../"

    lg.info("--- Please wait while we create+configure tenants through ssh.\n")
    lg.info("    This can take a while...\n")
    h1 = net.get("h1")
    cmd(h1, "python %s/tenant.py -m %d -T %d" % (testdir, args.num_hosts * 2, args.num_tenants))

    lg.info("\n--- Setting parameters for 100Mb/s\n")
    rootcmd("bash %s/100mbps.sh %s" % (dir, basedir))

def set_switch_rates(net):
    lg.info("--- Adding rate limits to switches.\n")
    BANDWIDTH="100Mbit"
    BOTTLENECK_LINKS=["s0-eth1"] # This is for SimpleTopo
    BOTTLENECK_LINKS=["s0-eth5", 's1-eth5'] # This is for Dumbell Topo
    BOTTLENECK_BW="80Mbit"
    for sw in net.switches:
        for intf in sw.intfs.itervalues():
            dev = intf.name
            if dev == "lo":
                continue
            bw = BANDWIDTH
            if dev in BOTTLENECK_LINKS:
                bw = BOTTLENECK_BW
            c = "tc qdisc add dev %s root handle 1: tbf limit 150000 burst 15000 rate %s" % (dev, bw)
            rootcmd(c)
    return

def change_tbf():
    dir = getdir()
    module = "%s/sch_tbf.ko" % dir
    if not os.path.exists(module):
        print "Please compile %s for ECN support."
        sys.exit(-1)
    rootcmd("rmmod sch_tbf; insmod %s;" % module)

def main():
    #topo = StarTopo(n=args.num_hosts)
    topo = Dumbell(n=args.num_hosts)
    change_tbf()
    net = Mininet(topo=topo, switch=LinuxBridge)
    net.start()
    dumpNodeConnections(net.hosts)
    ssh_init(net)
    mem_init(net)
    if args.conf:
        eyeq_conf(net)
    set_switch_rates(net)
    CLI(net)
    net.stop()
    rootcmd("pgrep -u memcache | xargs kill -9")
    rootcmd("pgrep -u root sshd | xargs kill -9")
    rootcmd("pgrep -u root screen | xargs kill -9")
    return

main()
