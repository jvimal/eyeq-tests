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

parser = argparse.ArgumentParser(description="Perfiso TX overhead test.")
parser.add_argument('--rate',
                    dest="rate",
                    action="store",
                    help="Rate of static rate limiter.",
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
                    help="Number of rate limiters.",
                    default=1)

parser.add_argument('-P',
                    dest="parallel",
                    action="store",
                    type=int,
                    help="Number of parallel connections per pair.",
                    default=4)

parser.add_argument('-t',
                    dest="t",
                    action="store",
                    type=int,
                    help="Time to run expt in seconds.",
                    default=120)

parser.add_argument('--rl',
                    dest="rl",
                    type=str,
                    choices=["perfiso", "htb", "hfsc"],
                    help="Choice of rate limiter.",
                    default="perfiso")

parser.add_argument('--timeout',
                    dest="timeout",
                    action="store",
                    help="Timeout for perfiso token bucket (in nano seconds).",
                    default=str(1000*1000))

args = parser.parse_args()

if int(args.timeout) <= 1000:
    print "Too low timeout, but nothing prevents you from setting it."
    sys.exit(0)

class TxOverhead(Expt):
    def configure_qdisc(self, host):
        dev = host.get_10g_dev()
        rate = self.opts("rate")
        n = self.opts("n")
        host.cmd("tc qdisc del dev %s root" % dev)
        host.cmd("tc qdisc add dev %s root handle 1: htb default 1000" % dev)
        for i in xrange(n):
            c = "tc class add dev %s parent 1: " % dev
            c += " classid 1:%d htb rate %sMbit" % (i+1, rate)
            host.cmd(c)
        for i in xrange(n):
            c = "tc filter add dev %s" % dev
            c += " parent 1: protocol ip prio 1 "
            c += " u32 match ip src %s classid 1:%d" % (host.get_tenant_ip(i+1), i+1)
            host.cmd(c)

    def start(self):
        h1 = Host("10.0.1.1")
        h2 = Host("10.0.1.2")
        hlist = HostList(h1, h2)
        self.hlist = hlist
        hlist.rmmod()
        hlist.remove_qdiscs()
        n = self.opts('n')
        hlist.prepare_iface()

        if self.opts('rl') == "perfiso":
            hlist.insmod()
            hlist.perfiso_set("ISO_VQ_DRAIN_RATE_MBPS", "11000")
            hlist.perfiso_set("ISO_MAX_TX_RATE", self.opts('rate'))
            hlist.perfiso_set("ISO_RFAIR_INITIAL", self.opts('rate'))
            hlist.perfiso_set("ISO_TOKENBUCKET_TIMEOUT_NS", self.opts('timeout'))
            for i in xrange(n):
                hlist.create_ip_tenant(i+1)
        else:
            self.configure_qdisc(h1)
            for i in xrange(n):
                hlist.create_ip_tenant(i+1)

        # Filter traffic to dest iperf port 5001+i to skb mark i+1
        hlist.cmd("killall -9 iperf; iptables -F")

        self.log("Starting CPU/bandwidth monitors")
        # Start monitors
        m = multiprocessing.Process(target=monitor_cpu, args=("%s/cpu.txt" % self.opts('dir'),))
        self.start_monitor(m)
        m = multiprocessing.Process(target=monitor_bw, args=("%s/net.txt" % self.opts('dir'),))
        self.start_monitor(m)
        m = multiprocessing.Process(target=monitor_perf,
                                    args=("%s/perf.txt" % self.opts('dir'), self.opts('t')))
        self.start_monitor(m)

        self.log("Starting %d iperfs" % n)
        # Start iperfs servers
        parallel = self.opts("P")
        iperf = Iperf({'-p': 5001,
                       '-P': parallel})
        server = iperf.start_server(h2.addr)
        self.procs.append(server)

        sleep(1)
        for i in xrange(n):
            ip = h2.get_tenant_ip(i+1)
            iperf = Iperf({'-p': 5001,
                           '-P': parallel,
                           '-c': ip,
                           '-B': h1.get_tenant_ip(i+1),
                           '-t': self.opts('t')})
            client = iperf.start_client(h1.addr)
            self.procs.append(client)

    def stop(self):
        self.hlist.remove_tenants()
        self.hlist.killall()
        for p in self.procs:
            p.kill()

TxOverhead({
        'n': args.n,
        'dir': args.dir,
        'rate': args.rate,
        't': args.t,
        'rl': args.rl,
        'timeout': args.timeout,
        'P': args.parallel,
        }).run()
