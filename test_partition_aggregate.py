from expt import Expt, progress
from host import *
from time import sleep
import subprocess
import argparse
import datetime
import sys
from collections import defaultdict

parser = argparse.ArgumentParser(description="Partition aggregate test.")
parser.add_argument('--create',
                    dest="create",
                    action="store_true",
                    help="Just create tenants",
                    default=False)

parser.add_argument('--destroy', '-c', '--clean',
                    dest="destroy",
                    action="store_true",
                    help="Just remove tenants",
                    default=False)

parser.add_argument('--mtu',
                    dest="mtu",
                    help="MTU",
                    default="9000")

parser.add_argument("--enabled", "--enable",
                    dest="enabled",
                    action="store_true",
                    help="Enable perfiso?",
                    default=False)

parser.add_argument("--weighted",
                    dest="weighted",
                    action="store_true",
                    help="Enable perfiso, but with weights?",
                    default=False)

parser.add_argument('--dir',
                    dest="dir",
                    default="/tmp/paggr")

parser.add_argument('--exptid',
                    dest="exptid",
                    default=None)

parser.add_argument('--time', '-t',
                    dest="t",
                    default=120)

parser.add_argument('--ntenants', '-n',
                    dest="ntenants",
                    type=int,
                    default=1)

parser.add_argument('--base',
                    dest="base",
                    type=int,
                    default=2)

parser.add_argument('--repeat',
                    dest="repeat",
                    type=int,
                    default=20000)

parser.add_argument('--size',
                    dest="size",
                    default='10K')

parser.add_argument('--bind',
                    dest="bind",
                    action="store_true",
                    default=False)

# tenant ids
TID = 1

args = parser.parse_args()

class PartitionAggregate(Expt):
    def create_tenants(self):
        n = self.opts("ntenants")
        for i in xrange(n):
            w = 1
            if self.opts("weighted"):
                w = self.get_tenant_weight(i)
            self.hlist.create_ip_tenant(TID+i, w)
        self.hlist.setup_tenant_routes(n)

    def get_tenant_weight(self, i):
        #return self.opts("base")**i
        return 1

    def get_tenant_P(self, i):
        return self.opts("base") ** i

    def start_pa_tenant(self, i, P=1):
        tid = TID + i
        self.start_pa_process(out="paggr-%s.txt" % i, tid=tid, P=P)

    def start_pa_process(self, out="paggr.txt", tid=1, cpu=None, P=1):
        dir = self.opts("dir")
        out = os.path.join(dir, out)
        CLIENT = "/root/vimal/exports/incast_app/l25_tcp_client"
        SERVER = "/root/vimal/exports/incast_app/l25_tcp_server"
        if cpu is None:
            cpu = self.nextcpu
            self.nextcpu = (self.nextcpu + 2) % 8
        for h in self.hlist.lst:
            ip = h.get_tenant_ip(tid)
            cmd = "mkdir -p %s; " % dir
            if args.bind:
                cmd += "taskset -c %s,%s  " % (cpu, cpu+1)
            cmd += " %s %s" % (SERVER, ip)
            h.cmd_async(cmd)

        print "Waiting for servers to start..."
        progress(1)
        print "starting client (tid=%s) on %s..." % (tid, host_ips[0])
        h0 = Host(host_ips[0])

        # Generate input file for client
        size = self.opts("size")
        inpfile = "~/vimal/exports/incast_app/input/get%s_P%s_tenant%s.dat" % (size, P, tid)
        cmd = "python tests/genconfig.py --traffic paggr -n 15 "
        cmd += "-P %s --size %s --repeat %s --tenant %s " % (P, size, self.opts("repeat"), tid)
        cmd += "> %s" % inpfile
        Popen(cmd, shell=True).wait()

        dir = self.opts("dir")
        outfile = os.path.join(dir, out)

        cmd = 'mkdir -p %s; ' % dir
        if args.bind:
            cmd += "taskset -c %s,%s  " % (cpu, cpu+1)
        cmd += " %s %s > %s" % (CLIENT, inpfile, outfile)
        h0.cmd_async(cmd)
        return

    def clean(self):
        self.hlist.killall("l25_tcp_client l25_tcp_server")
        self.hlist.remove_tenants()

    def start(self):
        hlist = HostList()
        self.nextcpu = 2
        self.completed = defaultdict(bool)
        for ip in host_ips:
            hlist.lst.append(Host(ip))
        self.hlist = hlist
        self.hlist.rmmod()
        if self.opts("create"):
            self.hlist.insmod()
            self.create_tenants()
            sys.exit(0)

        if self.opts("destroy"):
            self.clean()
            sys.exit(0)

        self.hlist.set_mtu(self.opts("mtu"))
        self.hlist.configure_tx_interrupt_affinity()
        if self.opts("enabled") or self.opts("weighted"):
            self.hlist.insmod()
        self.create_tenants()
        self.hlist.start_monitors(self.opts("dir"))
        for i in xrange(self.opts("ntenants")):
            self.start_pa_tenant(i, P=self.get_tenant_P(i))
        return

    def stop(self):
        if self.opts("create"):
            return
        if self.opts("destroy"):
            self.hlist.remove_tenants()
            return
        self.hlist.killall("l25_tcp_server l25_tcp_client")
        self.hlist.remove_tenants()
        for p in self.procs:
            p.kill()
        if args.exptid is None:
            args.exptid = "paggr-%s" % self.opts("size")
        self.hlist.copy("l1", self.opts("dir"), args.exptid)

PartitionAggregate(vars(args)).run()
