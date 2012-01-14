from expt import Expt, progress
from host import *
from time import sleep
import subprocess
import argparse
import datetime
import sys

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

parser.add_argument('--time', '-t',
                    dest="t",
                    default=120)

HADOOP_TID = 1
LOADGEN_TID = 2

args = parser.parse_args()

class Hadoop(Expt):
    def create_tenants(self):
        self.hlist.create_ip_tenant(HADOOP_TID)
        self.hlist.create_ip_tenant(LOADGEN_TID)
        self.hlist.setup_tenant_routes()

    def get_sort_id(self):
        # Jan-12--10-10
        return datetime.datetime.now().strftime("%h-%d--%H-%M")

    def start_dnsd(self):
        h1 = Host("10.0.1.1")
        print "Starting DNS server"
        h1.cmd_async("ruby ~/vimal/10g/dns/dnsd.rb > /dev/null 2>&1")
        sleep(5)

    def start_hadoop(self):
        self.master = Host("10.0.1.20")
        self.master.cmd("cd /usr/local/hadoop/conf;" +
                        "cp slaves.tenant1 slaves; cp masters.tenant1 masters;")
        self.start_dnsd()
        self.master.cmd("start-all.sh")
        progress(120)

        dir = self.opts("dir")
        cmd = "mkdir -p %s; cd /usr/local/hadoop; " % dir
        cmd += "hadoop jar hadoop-examples-0.20.205.0.jar "

        self.sid = self.get_sort_id()
        out = os.path.join(dir, "hadoop-progress.txt")
        cmd += "sort random-data sorted-data-%s " % self.sid
        cmd += " > %s 2>&1; " % out
        self.hadoop_job = self.master.cmd_async(cmd)

    def check_hadoop_done(self):
        out = self.master.cmd("hadoop job -list")
        lines = out.split("\n")
        for i in xrange(len(lines)):
            if "jobs currently running" in lines[i]:
                if i+2 < len(lines):
                    print lines[i+2]
        if "0 jobs currently running" in out:
            return True
        return False

    def stop_hadoop(self):
        try:
            self.master.cmd("stop-all.sh")
        except:
            self.hlist.lst[-1].cmd("stop-all.sh")

    def start_loadgen(self):
        dir = self.opts("dir")
        out = os.path.join(dir, "loadgen.txt")
        LOADGEN = "/root/vimal/exports/loadgen"
        # Start in all hosts
        traffic = self.opts("traffic")
        if traffic is None:
            return
        for h in self.hlist.lst:
            ip = h.get_tenant_ip(LOADGEN_TID)
            cmd = "mkdir -p %s; " % dir
            cmd += "%s -i %s " % (LOADGEN, ip)
            cmd += " -l 12345 -p 1000000 -f %s > %s" % (traffic, out)
            h.cmd_async(cmd)

        # Actually start it after 5minutes
        for h in self.hlist.lst:
            ip = h.get_tenant_ip(LOADGEN_TID)
            p = Popen("sleep 10; nc -nzv %s 12345" % ip, shell=True)
        return

    def clean(self):
        self.hlist.killall("loadgen ruby")
        self.hlist.cmd("stop-all.sh")
        self.hlist.remove_tenants()

    def start(self):
        hlist = HostList()
        for ip in host_ips:
            hlist.lst.append(Host(ip))
        self.hlist = hlist

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
        self.start_loadgen()
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
                    progress(240)
                continue
        except Exception, e:
            print "Hadoop job not found", e
        print "Hadoop job completed...", datetime.datetime.now()
        self.stop_hadoop()
        self.hlist.killall("ruby loadgen java")
        self.hlist.remove_tenants()
        for p in self.procs:
            p.kill()

Hadoop(vars(args)).run()
