from expt import Expt, progress
from host import *
from time import sleep
import subprocess
import argparse
import datetime
import sys
from collections import defaultdict

parser = argparse.ArgumentParser(description="Hadoop test.")
parser.add_argument('--create',
                    dest="create",
                    action="store_true",
                    help="Create tenants",
                    default=False)

parser.add_argument('--destroy', '-c', '--clean',
                    dest="destroy",
                    action="store_true",
                    help="Remove tenants",
                    default=False)

parser.add_argument('--mtu',
                    dest="mtu",
                    help="MTU",
                    default="9000")

parser.add_argument('--traffic',
                    dest="traffic",
                    help="traffic matrix",
                    default=None)

parser.add_argument('--size',
                    dest="size",
                    help="size of data to sort for trace",
                    default="1T")

# python tests/genconfig.py --time 10000 --type udp -n 16 \
# --traffic fullmesh --size 30G --inter 60 --repeat 10000

parser.add_argument("--enabled", "--enable",
                    dest="enabled",
                    action="store_true",
                    help="Enable perfiso?",
                    default=False)

parser.add_argument('--dir',
                    dest="dir",
                    default="/tmp")

parser.add_argument('--exptid',
                    dest="exptid",
                    default=None)

parser.add_argument('--time', '-t',
                    dest="t",
                    default=120)

HADOOP_TID = 1
LOADGEN_TID = 2

args = parser.parse_args()

class HadoopTrace(Expt):
    def create_tenants(self):
        self.hlist.create_ip_tenant(HADOOP_TID)
        self.hlist.create_ip_tenant(LOADGEN_TID)
        self.hlist.setup_tenant_routes()

    def start_hadoop(self):
        # Create loadgen file
        traffic = "~/vimal/exports/loadfiles/sort_%s" % self.opts("size")
        cmd = "python tests/genconfig.py --type tcp -n 16 -P 2 --tenant %s" % HADOOP_TID
        cmd += " --traffic sort --size %s" % self.opts("size")
        cmd += " --port %s > %s" % (12345+HADOOP_TID, traffic)
        print "Generating traffic matrix for sort"
        Popen(cmd, shell=True).wait()
        self.start_loadgen(out="sort.txt", tid=HADOOP_TID, traffic=traffic)

    def check_hadoop_done(self):
        # Sort is running on a host if file /dir/sort.txt exists and
        # "client thread terminated" has not been printed yet in that
        # file
        f = os.path.join(self.opts("dir"), "sort.txt")
        done = True
        for h in self.hlist.lst:
            cmd = "if [ -f %s ]; then grep 'client thread terminated' %s; " % (f, f)
            cmd += "else echo 'sort not running'; fi"
            out = h.cmd(cmd)
            nr = 'not running' in out
            tt = 'thread terminated' in out
            if nr or tt:
                if not self.completed[h.addr]:
                    if nr:
                        print 'Not running in %s' % h.addr
                    elif tt:
                        print 'Completed in %s' % h.addr
                    self.completed[h.addr] = True
                done = done and True
            else:
                done = False
        return done

    def start_loadgen(self, out="loadgen.txt", tid=2, traffic=None):
        dir = self.opts("dir")
        out = os.path.join(dir, out)
        LOADGEN = "/root/vimal/exports/loadgen"
        # Start in all hosts
        if traffic is None:
            return
        port = 12345 + tid
        for h in self.hlist.lst:
            ip = h.get_tenant_ip(tid)
            cmd = "mkdir -p %s; " % dir
            cmd += "%s -i %s -vv " % (LOADGEN, ip)
            cmd += " -l %s -p 1000000 -f %s > %s" % (port, traffic, out)
            h.cmd_async(cmd)

        print "Waiting for loadgen to start..."
        progress(20)
        for h in self.hlist.lst:
            ip = h.get_tenant_ip(tid)
            p = Popen("nc -nzv %s %s" % (ip, port), shell=True)
        return

    def clean(self):
        self.hlist.killall("loadgen ruby")
        self.hlist.remove_tenants()

    def start(self):
        hlist = HostList()
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
        if self.opts("enabled"):
            self.hlist.insmod()
        self.create_tenants()
        self.start_hadoop()
        self.start_loadgen(tid=LOADGEN_TID, traffic=self.opts("traffic"))
        return

    def stop(self):
        if self.opts("create"):
            return
        if self.opts("destroy"):
            self.hlist.remove_tenants()
            return
        try:
            while 1:
                done = self.check_hadoop_done()
                if done:
                    break
                else:
                    print "Waiting for hadoop job...", datetime.datetime.now()
                    try:
                        progress(60)
                    except:
                        break
                continue
        except Exception, e:
            print "Hadoop job not found", e
        print "Hadoop job completed...", datetime.datetime.now()
        self.hlist.killall("ruby loadgen java")
        self.hlist.remove_tenants()
        for p in self.procs:
            p.kill()
        if args.exptid is None:
            args.exptid = "sort-%s-trace" % self.opts("size")
        self.hlist.copy("l1", self.opts("dir"), args.exptid)

HadoopTrace(vars(args)).run()
