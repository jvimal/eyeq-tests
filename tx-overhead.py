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
    def configure_qdisc(self):
        dev="eth2"
        rate = self.opts("rate")
        n = self.opts("n")
        cmd("tc qdisc del dev %s root" % dev)
        cmd("tc qdisc add dev %s root handle 1: htb default 1000" % dev)
        for i in xrange(n):
            cmd("tc class add dev %s parent 1: classid 1:%d htb rate %sMbit" % (dev, i+1, rate))
        for i in xrange(n):
            c = "tc filter add dev %s" % dev
            c += " parent 1: protocol ip prio %d handle %d fw classid 1:%d" % (i+1, i+1, i+1)
            cmd(c)

    def start(self):
        h1 = Host("192.168.1.1")
        h2 = Host("192.168.1.2")
        hlist = HostList(h1, h2)
        hlist.rmmod()
        remove_qdiscs()
        n = self.opts('n')

        if self.opts('rl') == "perfiso":
            h1.insmod()
            h1.perfiso_set("ISO_MAX_TX_RATE", self.opts('rate'))
            h1.perfiso_set("ISO_MAX_TX_RATE", self.opts('rate'))
            h1.perfiso_set("ISO_RFAIR_INITIAL", self.opts('rate'))
            h1.perfiso_set("ISO_TOKENBUCKET_TIMEOUT_NS", self.opts('timeout'))
            for i in xrange(n):
                h1.perfiso_create_txc(i+1)
        else:
            self.configure_qdisc()

        # Filter traffic to dest iperf port 5001+i to skb mark i+1
        hlist.cmd("killall -9 iperf; iptables -F")
        self.log("Adding iptables classifiers")

        for i in xrange(n):
            klass = i+1
            c = "iptables -A OUTPUT --dst 192.168.2.2"
            c += " -p tcp --dport %d -j MARK --set-mark %d" % (5000 + klass, klass)
            h1.cmd(c)

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
        for i in xrange(n):
            klass = i+1
            port = 5000 + klass
            iperf = Iperf({'-p': port,
                           '-P': parallel,
                           '-c': '192.168.2.2'})
            server = iperf.start_server('192.168.2.2')
            self.procs.append(server)
            self.log("server %d" % klass)
            sleep(0.1)

        sleep(1)
        for i in xrange(n):
            klass = i+1
            port = 5000 + klass
            iperf = Iperf({'-p': port,
                           '-P': parallel,
                           '-c': '192.168.2.2',
                           '-t': self.opts('t')})
            client = iperf.start_client('192.168.2.1')
            self.procs.append(client)
            self.log("client %d" % klass)

    def stop(self):
        for p in self.procs:
            p.kill()
        killall()

TxOverhead({
        'n': args.n,
        'dir': args.dir,
        'rate': args.rate,
        't': args.t,
        'rl': args.rl,
        'timeout': args.timeout,
        'P': args.parallel,
        }).run()
