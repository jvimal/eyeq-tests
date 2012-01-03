from host import *
import argparse
from time import sleep
import subprocess
import sys

parser = argparse.ArgumentParser("Frontend to Siva's loadgen program.")

parser.add_argument('--start',
                    dest='start',
                    action="store_true",
                    default=False)

parser.add_argument('--stop',
                    dest="stop",
                    action="store_true",
                    default=True)

parser.add_argument('--cpu',
                    dest="cpu",
                    default=None)

parser.add_argument('--dryrun',
                    dest="dryrun",
                    action="store_true",
                    default=False)

parser.add_argument('--dir',
                    dest="dir",
                    default="/tmp")

parser.add_argument('--traffic',
                    dest="traffic",
                    help="Traffic description",
                    required=True,
                    default=None)

LOADGEN_NAME="loadgen"
LOADGEN="/root/vimal/exports/%s" % LOADGEN_NAME
PORT=12345
SAMPLE_PERIOD=500000

args = parser.parse_args()
if args.start:
    args.stop = False
if args.stop:
    args.start = False

if not os.path.exists(args.traffic):
    print "file %s does not exist" % args.traffic
    sys.exit(0)

hosts = []
hlist = HostList()

for h in host_ips:
    hst = Host(h)
    hosts.append(hst)
    hlist.append(hst)

def pre():
    # Start the servers
    out = os.path.join(args.dir, "loadgen.txt")
    for h in hosts:
        # 'ip' should be for all tenants in host 'h'
        # List of tenants can be obtained from the config file
        ip = h.get_10g_ip()
        loadgen_args = "-i %s -l %s -p %s -f %s" % (ip, PORT, SAMPLE_PERIOD, args.traffic)
        cmd = "%(exec)s %(args)s > %(out)s" % {
            'exec': LOADGEN,
            'args': loadgen_args,
            'out': out }
        h.cmd_async("killall -9 %s; mkdir -p %s; %s" % (LOADGEN_NAME, args.dir, cmd),
                    args.dryrun)
    sleep(2)

def start():
    pre()
    # Send start command, by just connecting to host,port
    execs = []
    for h in hosts:
        ip = h.get_10g_ip()
        if not args.dryrun:
            execs.append(subprocess.Popen("nc -zv %s %s" % (ip, PORT), shell=True))
    for e in execs:
        e.wait()
    return

def stop():
    for h in hosts:
        cmd = "killall -9 %s" % LOADGEN_NAME
        h.cmd_async(cmd, args.dryrun)
    return

if args.start:
    start()
if args.stop:
    stop()
