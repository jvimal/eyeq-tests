from host import *
import argparse
from time import sleep

parser = argparse.ArgumentParser()

parser.add_argument('--start',
                    dest='start',
                    action="store_true",
                    default=False)

parser.add_argument('--stop',
                    dest="stop",
                    action="store_true",
                    default=True)

parser.add_argument('-P',
                    dest="P",
                    default=4)

parser.add_argument('--cpu',
                    dest="cpu",
                    default=None)

args = parser.parse_args()
if args.start:
    args.stop = False
if args.stop:
    args.start = False

hosts = []
hlist = HostList()

for h in host_ips:
    hst = Host(h)
    hosts.append(hst)
    hlist.append(hst)

def iperf_server():
    cmd = "iperf -s"
    if args.cpu:
        cmd = "taskset -c %s %s" % (args.cpu, cmd)
    return cmd

def iperf_client(dst,time='3600'):
    cmd = "iperf -c %s -P %s -t %s" % (dst.get_10g_ip(), args.P, time)
    if args.cpu:
        cmd = "taskset -c %s %s" % (args.cpu, cmd)
    return "(%s &)" % cmd

def start_mesh():
    for h in hosts:
        h.cmd_async(iperf_server())
        h.configure_rps()

    sleep(2)
    for i,hi in enumerate(hosts):
        hi.delay = True
        for j,hj in enumerate(hosts):
            if i == j:
                continue
            hi.cmd_async(iperf_client(hj))
        hi.delayed_async_cmds_execute()
    return

def stop_mesh():
    hlist.cmd("killall -9 iperf")

if args.start:
    start_mesh()
if args.stop:
    stop_mesh()
