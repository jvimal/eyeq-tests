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

parser = argparse.ArgumentParser(description="Memcached Cluster Test.")
parser.add_argument('--ns',
                    dest="ns",
                    type=int,
                    help="Number of servers.",
                    default=4)

parser.add_argument('--nc',
                    dest="nc",
                    type=int,
                    help="Number of clients.",
                    default=12)

parser.add_argument('--enable', '--enabled',
                    dest="enable",
                    help="Enable isolation.",
                    action="store_true",
                    default=False)

parser.add_argument('--dir',
                    dest="dir",
                    help="Directory to store output.",
                    required=True)

parser.add_argument('--exptid',
                    dest="exptid",
                    help="Experiment ID",
                    default=None)

parser.add_argument('--memaslap',
                    dest="memaslap",
                    help="Memaslap config file",
                    default=None)

parser.add_argument('--traffic',
                    dest="traffic",
                    help="Cross traffic matrix for loadgen.",
                    default=None)

parser.add_argument('--time', '-t',
                    dest="t",
                    type=int,
                    help="Time to run the experiment",
                    default=300)

parser.add_argument('--mtu',
                    dest="mtu",
                    help="MTU of 10G interface",
                    default='1500')

parser.add_argument('--dryrun',
                    dest="dryrun",
                    help="Don't execute experiment commands.",
                    action="store_true",
                    default=False)

parser.add_argument('--active',
                    dest="active",
                    help="Which tenants are active? (udp/mem/udp,mem)",
                    default="udp,mem")

parser.add_argument('--nconn',
                    dest="nconn",
                    help="Number of active connections per memcached server",
                    type=int,
                    default=128)

parser.add_argument('--mcperf',
                    dest="mcperf",
                    help="Use mcperf instead of memaslap",
                    action="store_true",
                    default=False)

parser.add_argument('--mcexp',
                    dest="mcexp",
                    help="inter-req arrival time exponential",
                    action="store_true",
                    default=False)

parser.add_argument('--mcsize',
                    dest="mcsize",
                    help="mcperf: Size of requests",
                    default="1000")

parser.add_argument('--mcrate',
                    dest="mcrate",
                    help="mcperf: Request generation rate",
                    default="6000")

parser.add_argument('--static',
                    dest="static",
                    action="store_true",
                    help="Static bandwidth for UDP",
                    default=False)

args = parser.parse_args()
MEMASLAP_TID = 1
LOADGEN_TID = 2

class MemcachedCluster(Expt):
    def initialise(self):
        self.hlist.rmmod()
        self.hlist.remove_qdiscs()
        if self.opts("enable"):
            self.hlist.insmod()
        # Create a static rate limiter for UDP tenant
        if self.opts("static"):
            for h in self.hlist.lst:
                h.create_ip_tx_rl(ip=h.get_tenant_ip(LOADGEN_TID), rate='5Gbit', static=True)

    def prepare_iface(self):
        h = self.hlist
        h.set_mtu(self.opts("mtu"))

        if self.opts("enable"):
            h.prepare_iface()
            h.create_ip_tenant(MEMASLAP_TID)
            h.create_ip_tenant(LOADGEN_TID)

    def memaslap(self, host, dir="/tmp"):
        time = int(self.opts("t")) - 5
        config = self.opts("memaslap")
        active = self.opts("active")
        if config is None:
            return
        if "mem" not in active:
            return
        servers = []
        for h in self.hs.lst:
            ip = h.get_10g_ip()
            if self.opts("enable"):
                ip = h.get_tenant_ip(MEMASLAP_TID)
            servers.append("%s:11211" % ip)
        servers = ",".join(servers)

        cmd = "rm -rf %s; mkdir -p %s; " % (dir, dir)
        cmd += "memaslap -s %s " % servers
        cmd += "-S 1s -t %ss " % time
        cmd += "-c %s -T 4 -B -F %s " % (self.opts("nconn") * len(self.hs.lst), config)
        cmd += " > %s/memaslap.txt" % dir
        host.cmd_async(cmd)

    def mcperf(self, host, dir="/tmp"):
        time = int(self.opts("t")) - 5
        if "mem" not in self.opts("active"):
            return
        servers = []
        host.cmd("rm -rf %s; mkdir -p %s;" % (dir, dir))
        nconn =  self.opts("nconn")
        mcrate = self.opts("mcrate")

        if self.opts("mcexp"):
            rate = "e%.5f" % (1.0 / (float(mcrate) / nconn))
        else:
            # Divide rate equally among subconnections
            rate = int(mcrate) / nconn

        for tid, h in enumerate(self.hs.lst):
            ip = h.get_10g_ip()
            if self.opts("enable"):
                ip = h.get_tenant_ip(MEMASLAP_TID)

            N = int(self.opts("mcrate")) * time
            workload = "get"
            if "set" in self.opts("memaslap"):
                workload = "set"

            cmd = "(mcperf -s %s " % (ip)
            cmd += "-N %s -R %s " % (N, rate)
            cmd += "-z d%s " % (self.opts("mcsize"))
            cmd += "-H -m %s -T %s " % (workload, time)
            cmd += "-n %s --conn-rate %s " % (nconn, nconn)
            cmd += "> %s/mcperf-%s-%s.txt); " % (dir, tid, ip)
            host.cmd_async(cmd)
        return

    def loadgen(self, host, traffic=None, dir="/tmp"):
        if traffic is None:
            return
        active = self.opts("active")
        if "udp" not in active:
            return
        out = os.path.join(dir, "loadgen.txt")
        LOADGEN = "/root/vimal/exports/loadgen "
        ip = host.get_10g_ip()
        if self.opts("enable"):
            ip = host.get_tenant_ip(LOADGEN_TID)
        cmd = "%s -i %s " % (LOADGEN, ip)
        cmd += " -l 12345 -p 500000 -f %s > %s" % (traffic, out)
        host.cmd_async(cmd)

    def loadgen_start(self):
        if "udp" not in self.opts("active"):
            return
        procs = []
        for h in self.hlist.lst:
            ip = h.get_10g_ip()
            if self.opts("enable"):
                ip = h.get_tenant_ip(LOADGEN_TID)
            sleep(2)
            p = Popen("nc -nzv %s 12345" % ip, shell=True)
            procs.append(p)
        for p in procs:
            p.wait()
        return

    def start(self):
        # num servers, num clients
        ns = self.opts("ns")
        nc = self.opts("nc")
        dir = self.opts("dir")
        xtraffic = self.opts("traffic")

        assert(ns + nc <= len(host_ips))
        hservers = HostList()
        hclients = HostList()
        hlist = HostList()

        for i in xrange(ns):
            ip = pick_host_ip(i)
            h = Host(ip)
            hservers.append(h)
            hlist.append(h)
            self.log(T.colored(ip, "green"))

        for i in xrange(ns, ns+nc):
            ip = pick_host_ip(i)
            h = Host(ip)
            hclients.append(h)
            hlist.append(h)
            self.log(T.colored(ip, "yellow"))

        self.hs = hservers
        self.hc = hclients
        self.hlist = hlist
        hlist.set_dryrun(self.opts("dryrun"))
        self.initialise()
        # Automatically initialised by the module
        #hlist.perfiso_set("IsoAutoGenerateFeedback", "1")
        #hlist.perfiso_set("ISO_VQ_DRAIN_RATE_MBPS", 8500)
        #hlist.perfiso_set("ISO_VQ_UPDATE_INTERVAL_US", 25)
        self.prepare_iface()
        self.hlist.setup_tenant_routes(2)

        hservers.start_memcached()
        sleep(2)
        for h in hclients.lst:
            if args.mcperf:
                self.mcperf(h, dir)
            else:
                self.memaslap(h, dir)

        hlist.start_monitors(dir)
        self.hlist.netstat_begin(self.opts("dir"))

        for h in hlist.lst:
            self.loadgen(h, xtraffic, dir)
        self.loadgen_start()

    def stop(self):
        self.hlist.netstat_end(self.opts("dir"))
        self.hlist.killall("memcached loadgen")
        self.hlist.remove_tenants()
        self.hlist.copy("l1", self.opts("dir"), self.opts("exptid"))
        return

MemcachedCluster(vars(args)).run()
