
from mininet.topo import Topo
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.net import Mininet
from mininet.log import lg, info, setLogLevel
from mininet.util import dumpNodeConnections, quietRun, moveIntf
from mininet.cli import CLI
from mininet.node import Switch

from subprocess import Popen, PIPE, check_output
from time import sleep, time
from multiprocessing import Process
from argparse import ArgumentParser

import sys
import os
import termcolor as T
import time

setLogLevel('info')

LEAF=1
SPINE=2
CONTROL_IFACES=["eth0", "lo"]
IFENSLAVE='/sbin/ifenslave'

parser = ArgumentParser("Configure a routed network in Mininet.")
parser.add_argument('--ecmp',
                    choices=["packet", "flow"],
                    default="flow")
parser.add_argument('--reorder',
                    type=int,
                    help="How much reordering to tolerate before fast retransmit",
                    default=3)
parser.add_argument('--bw',
                    help="Link capacity",
                    default="100Mbit")
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

def log(s, col="green"):
    print T.colored(s, col)

if args.ecmp == "packet":
    if not os.path.exists(IFENSLAVE):
        raise Exception("Need ifenslave for per-packet ECMP.")

if args.bw == "0":
    log("Not setting link rates")
    args.bw = None

def HostIP(leaf, hostid):
    return "10.0.%d.%d" % (leaf, hostid)

def LeafIP(num):
    return "10.0.%d.254" % (num)

def LeafNet(num):
    return "10.0.%d.0/24" % num

def SpineIP(num):
    if args.ecmp == "flow":
        return "10.%d.0.254" % (num)
    elif args.ecmp == "packet":
        # All spines have the same IP
        return "10.1.0.254"

def SpineMAC(num):
    if args.ecmp == "flow":
        return "00:00:00:%x:00:00" % num
    elif args.ecmp == "packet":
        return "00:00:00:01:00:00"

def LeafMAC(num):
    return "00:00:00:00:%x:00" % num

def setMac(node, intf, mac):
    # To prevent accidental stupidity.
    assert(intf not in CONTROL_IFACES)
    cmd = "ifconfig %s down; ifconfig %s hw ether %s; ifconfig %s up" % (intf, intf, mac, intf)
    node.cmd(cmd)

def rateCmds(intf, rate):
    return []
    return ["tc qdisc add dev %s root handle 1: htb default 1" % intf,
            "tc class add dev %s classid 1:1 parent 1: htb rate %s" % (intf, rate),
            "tc qdisc add dev %s handle 10: parent 1:1 pfifo limit 100" % (intf)
            ]

class Routed(Switch):
    ID = 0
    def __init__(self, name, **kwargs):
        kwargs['inNamespace'] = True
        Switch.__init__(self, name, **kwargs)
        print "Switch %s %s" % (name, self.inNamespace)
        Routed.ID += 1
        self.switch_id = Routed.ID
        self.kind = kwargs.get('kind')

        self.num_leafs = kwargs.get('num_leafs')
        self.num_spines = kwargs.get('num_spines')
        self.hosts_per_leaf = kwargs.get('hosts_per_leaf')

    @staticmethod
    def setup():
        pass

    def start(self, controllers):
        # Initialise
        self.cmd("sysctl -w net.ipv4.ip_forward=1")
        self.cmd("ifconfig %s-eth1 0" % (self.name))
        ip = None
        if self.kind == LEAF:
            ip = LeafIP(self.switch_id)
        elif self.kind == SPINE:
            ip = SpineIP(self.switch_id - self.num_leafs)
        else:
            raise Exception("Neither leaf nor spine router")

        cmd = "ifconfig %s-eth1 %s" % (self.name, ip)
        self.cmd(cmd)
        if self.kind == LEAF:
            self.configureLeafRoutes()
        else:
            self.configureSpineRoutes()

        if args.bw:
            self.configureRates()

    def configureRates(self):
        rate = args.bw
        for intf in self.intfs.values():
            for cmd in rateCmds(intf, rate):
                self.cmd(cmd)
        return

    def configureSpineRoutes(self):
        if args.ecmp == "packet":
            # Set Mac addresses on all intfs correctly
            for i in xrange(self.num_leafs):
                intf = "%s-eth%d" % (self.name, 1+i)
                macaddr = SpineMAC(self.switch_id)
                setMac(self, intf, macaddr)

            # Set static arp for all leaves
            for leaf in xrange(self.num_leafs):
                leaf += 1
                ip = LeafIP(leaf)
                mac = LeafMAC(leaf)
                intf = "%s-eth%d" % (self.name, leaf)
                cmd = "arp -s -i %s %s %s" % (intf, ip, mac)
                self.log(cmd)
                self.cmd(cmd)

        for i, intf in enumerate(self.intfs.values()):
            dest = LeafIP(1+i)
            net = LeafNet(1+i)
            cmd = "route add -host %s dev %s" % (dest, intf)
            self.cmd(cmd)
            cmd = "route add -net %s dev %s gw %s" % (net, intf, dest)
            self.cmd(cmd)
        return

    def configureLeafRoutes(self):
        # configure routes to all hosts
        for i, intf in enumerate(self.intfs.values()):
            dest = HostIP(self.switch_id, 1 + i)
            metric = 1
            cmd = "route add -host %s dev %s metric %d" % (dest, intf, metric)
            self.log(cmd)
            self.cmd(cmd)

        if args.ecmp == "flow":
            self.configureLeafFlowECMP()
        else:
            self.configureLeafPacketECMP()

    def configureLeafFlowECMP(self):
        # Conf leaves to other spines
        for spine in xrange(self.num_spines):
            spine += 1
            intf = "%s-eth%d" % (self.name, spine+self.hosts_per_leaf)
            sip = SpineIP(spine)
            cmd = "route add -host %s dev %s" % (sip, intf)
            self.log(cmd, "yellow")
            self.cmd(cmd)

        # Configure routes to other leaves
        for leaf in xrange(self.num_leafs):
            leaf += 1
            if leaf == self.switch_id:
                continue
            net = LeafNet(leaf)

            # If you want ecmp
            args = ""
            for sid, intfid in enumerate(xrange(self.num_spines)):
                sid += 1
                weight = 1
                intf = "%s-eth%d" % (self.name, 1+intfid+self.hosts_per_leaf)
                gw = SpineIP(sid)
                args += " nexthop via %s dev %s weight %s " % (gw, intf, weight)

            self.log("ECMP: " + args)
            self.cmd("ip route add %s %s" % (net, args))
            # If you want to do failover...
            """
            for sid, intfid in enumerate(xrange(self.num_spines)):
                sid += 1
                metric = 1
                intf = "%s-eth%d" % (self.name, 1 + intfid + self.hosts_per_leaf)
                gw = SpineIP(sid)
                cmd = "route add -net %s dev %s metric %d gw %s" % (net, intf, metric, gw)
                self.log(cmd, "yellow")
                self.cmd(cmd)
            """
        return

    def configureLeafPacketECMP(self):
        # per-packet ECMP using bond device and RR.
        # Insert one bond device per leaf.
        bond = "bond%d" % self.switch_id
        # Move bond intf to each leaf.
        moveIntf(bond, self)
        # configure mac-address on bond interface
        mac = LeafMAC(self.switch_id)
        setMac(self, bond, mac)
        # enslave all links to spines
        intfs = []
        for spine in xrange(self.num_spines):
            intf = "%s-eth%d" % (self.name, 1+spine+self.hosts_per_leaf)
            intfs.append(intf)
        cmd = "ifconfig %s up; ifenslave %s %s" % (bond, bond, ' '.join(intfs))
        self.log(cmd)
        self.cmd(cmd)
        # configure routes to spines; in this case all spines have the
        # same IP address.
        spine_ip = SpineIP(0)
        cmd = "route add -host %s dev %s" % (spine_ip, bond)
        self.cmd(cmd)

        # configure routes to all other leaves
        for leaf in xrange(self.num_leafs):
            leaf += 1
            if leaf == self.switch_id:
                continue
            net = LeafNet(leaf)
            sip = SpineIP(0)
            cmd = "ip route add %s nexthop via %s dev %s" % (net, sip, bond)
            self.cmd(cmd)
        # set spine mac address
        sip = SpineIP(0)
        mac = SpineMAC(0)
        cmd = "arp -s -i %s %s %s" % (bond, sip, mac)
        self.cmd(cmd)
        return

    def stop(self):
        self.deleteIntfs()

    def log(self, s, col="magenta"):
        print T.colored(s, col)

class LeafSpine(Topo):
    def __init__(self, hosts_per_leaf=4,
                 num_leafs=4, num_spines=4):
        # Add default members to class.
        super(LeafSpine, self ).__init__()

        num_hosts = hosts_per_leaf * num_leafs
        self.num_hosts = num_hosts
        self.hosts_per_leaf = hosts_per_leaf
        self.num_leafs = num_leafs
        self.num_spines = num_spines
        topoargs = dict(num_hosts=num_hosts,
                        hosts_per_leaf=hosts_per_leaf,
                        num_leafs=num_leafs,
                        num_spines=num_spines)
        leafs = []
        spines = []
        # Create switch and host nodes
        for i in xrange(num_hosts):
            self.addNode('h%d' % (i+1))

        for i in xrange(num_leafs):
            leaf = self.addSwitch('l%d' % (i+1), kind=LEAF, **topoargs)
            leafs.append(leaf)

        for i in xrange(num_spines):
            spine = self.addSwitch('s%d' % (i+1), kind=SPINE, **topoargs)
            spines.append(spine)

        for i in xrange(num_hosts):
            leaf_id = (1 + i / hosts_per_leaf)
            leaf = 'l%d' % leaf_id
            host = 'h%d' % (i+1)
            self.addLink(host, leaf)

        for i in xrange(num_leafs):
            for j in xrange(num_spines):
                leaf = 'l%d' % (i+1)
                spine = 's%d' % (j+1)
                self.addLink(leaf, spine)
        return

def init():
    if args.ecmp == "packet":
        quietRun("rmmod bonding")
        quietRun("modprobe bonding max_bonds=20")

    log("Setting tcp reordering to %s" % args.reorder)
    quietRun("sysctl -w net.ipv4.tcp_reordering=%s" % (args.reorder))

def cmd(h, c, **kwargs):
    if not kwargs.get("quiet", False):
        print c
    h.sendCmd(c)
    h.waitOutput()

def rootcmd(c, **kwargs):
    if not kwargs.get("quiet", False):
        print c
    Popen(c, shell=True).wait()

def setHostRate(host):
    rate = args.bw
    intf = "%s-eth0" % (host.name)
    for cmd in rateCmds(intf, rate):
        host.cmd(cmd)
    return

def configHostRoutes(net, topo):
    for id, host in enumerate(net.hosts):
        name = host.name
        leaf_id = 1 + id / topo.hosts_per_leaf
        leaf_ip = LeafIP(leaf_id)
        host_ip = HostIP(leaf_id, 1 + id % topo.hosts_per_leaf)
        cmd = "ifconfig %s-eth0 %s" % (name, host_ip)
        host.cmd(cmd)
        cmd = "route add -net 10.0.0.0/8 gw %s dev %s-eth0" % (leaf_ip, name)
        print cmd
        host.cmd(cmd)

def change_tbf():
    dir = getdir()
    module = "%s/sch_tbf.ko" % dir
    if not os.path.exists(module):
        print "Please compile %s for ECN support."
        sys.exit(-1)
    rootcmd("rmmod sch_tbf; insmod %s;" % module)

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

def ssh_init(net):
    lg.info("--- Starting sshd inside all hosts\n")
    for host in net.hosts:
        cmd(host, "/usr/sbin/sshd", quiet=True)
        #p = host.popen("/usr/sbin/sshd")
    return

def set_switch_rates(net):
    lg.info("--- Adding rate limits to switches.\n")
    BANDWIDTH="100Mbit"
    BOTTLENECK_LINKS=["s0-eth1"] # This is for SimpleTopo
    BOTTLENECK_LINKS=["s0-eth5", 's1-eth5'] # This is for Dumbell Topo
    BOTTLENECK_LINKS=[]
    BOTTLENECK_BW="80Mbit"
    for sw in net.hosts:
        if not (sw.name.startswith('l') or sw.name.startswith('s')):
            continue
        for intf in sw.intfs.itervalues():
            dev = intf.name
            if dev == "lo" or dev.startswith('bond'):
                print 'skipping', dev
                continue
            bw = BANDWIDTH
            if dev in BOTTLENECK_LINKS:
                bw = BOTTLENECK_BW
            c = "tc qdisc add dev %s root handle 1: tbf limit 150000 burst 15000 rate %s" % (dev, bw)
            rootcmd(c)
    return


def main():
    init()
    topo = LeafSpine()
    net = Mininet(topo=topo,
                  host=CPULimitedHost,
                  link=TCLink,
                  switch=Routed)
    net.start()
    ssh_init(net)
    configHostRoutes(net, topo)
    if args.conf:
        eyeq_conf(net)
    set_switch_rates(net)
    CLI(net)
    rootcmd("pgrep -u root sshd | xargs kill -9")
    net.stop()

if __name__ == "__main__":
    main()
