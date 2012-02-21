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

parser.add_argument('--nhadoop', '-n',
                    dest="nhadoop",
                    type=int,
                    default=1)

parser.add_argument('--static',
                    dest="static",
                    action="store_true",
                    help="Static bandwidth for UDP",
                    default=False)

LOADGEN_TID = 1
# hadoop tenant ids start from 2
HADOOP_TID = 2

args = parser.parse_args()

class HadoopTrace(Expt):
    def create_tenants(self):
        self.hlist.create_ip_tenant(LOADGEN_TID)
        if self.opts("static"):
            for h in self.hlist.lst:
                h.create_ip_tx_rl(ip=h.get_tenant_ip(LOADGEN_TID), rate='5Gbit', static=True)
        else:
            self.hlist.remove_qdiscs()
        n = args.nhadoop-1
        for i in xrange(args.nhadoop):
            self.hlist.create_ip_tenant(HADOOP_TID+i)
        self.hlist.setup_tenant_routes(args.nhadoop+1)

    def get_hadoop_P(self, i):
        return 3**i

    def start_hadoop(self, i, P=1):
        # Create loadgen file
        tid = HADOOP_TID + i
        traffic = "~/vimal/exports/loadfiles/sort_%s_%s" % (self.opts("size"), tid)
        cmd = "python tests/genconfig.py --type tcp -n 16 -P %s --tenant %s" % (P, tid)
        cmd += " --traffic sort --size %s" % self.opts("size")
        cmd += " --port %s > %s" % (12345+tid, traffic)
        print "Generating traffic matrix for sort for hadoop %s" % i
        Popen(cmd, shell=True).wait()
        self.start_loadgen(out="sort-%s.txt" % i, tid=tid, traffic=traffic)

    def check_hadoop_done(self, i):
        # Sort is running on a host if file /dir/sort.txt exists and
        # "client thread terminated" has not been printed yet in that
        # file
        f = os.path.join(self.opts("dir"), "sort-%s.txt" % i)
        done = True
        done_count = 0
        total_count = 0
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
                done_count += 1
            else:
                done = False
            total_count += 1
        print '%d/%d' % (done_count, total_count)
        return done

    def start_loadgen(self, out="loadgen.txt", tid=2, traffic=None, cpu=None):
        dir = self.opts("dir")
        out = os.path.join(dir, out)
        LOADGEN = "/root/vimal/exports/loadgen"
        # Start in all hosts
        if traffic is None:
            return
        if cpu is None:
            cpu = self.nextcpu
            self.nextcpu = (self.nextcpu + 2) % 8
        port = 12345 + tid
        for h in self.hlist.lst:
            ip = h.get_tenant_ip(tid)
            cmd = "mkdir -p %s; " % dir
            cmd += "taskset -c %s,%s %s -i %s -vv " % (cpu, cpu+1, LOADGEN, ip)
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
        if self.opts("enabled"):
            self.hlist.insmod()
        self.create_tenants()
        self.hlist.start_monitors(self.opts("dir"))
        for i in xrange(self.opts("nhadoop")):
            self.start_hadoop(i, P=self.get_hadoop_P(i))
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
                done = True
                for i in xrange(self.opts("nhadoop")):
                    done = done and self.check_hadoop_done(i)
                if done:
                    break
                else:
                    print "Waiting for hadoop job(s)...", datetime.datetime.now()
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
