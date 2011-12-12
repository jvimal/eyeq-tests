
from subprocess import Popen
from time import sleep
import paramiko
import termcolor as T

default_dir='/tmp'
SSH_PREFIX = "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no "

sshs = {}

def cmd(s):
    return Popen(s, shell=True).wait()

def cmd_async(s):
    return Popen(s, shell=True)

def cmd_host(host, c):
    global sshs
    ssh = sshs.get(host, None)
    if ssh is None:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username='root')
        sshs[host] = ssh
    #ssh = SSH_PREFIX + " %s \"%s\" > /dev/null 2>&1" % (host, c)
    #return Popen(ssh, shell=True).wait()
    print T.colored(host + ":", "magenta"), T.colored(c, "grey", attrs=["bold"])
    out = ssh.exec_command(c)[1].read()
    return out

def cmd_host_async(host, c):
    #ssh = SSH_PREFIX + " %s \"%s\" > /dev/null 2>&1" % (host, c)
    #return Popen(ssh, shell=True)
    ssh = sshs.get(host, None)
    if ssh is None:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username="root")
        sshs[host] = ssh
    out = ssh.exec_command(c)
    return out

def unload_module():
    cmd("rmmod perfiso")
    sleep(1)

def load_module():
    cmd("insmod %s iso_param_dev=%s" % (PI_MODULE, PI_DEV))
    sleep(1)

def reload_module():
    unload_module()
    load_module()

def remove_qdiscs(dev="eth2"):
    cmd("tc qdisc del dev %s root" % dev)

def killall(progs=""):
    s = "killall -9 ssh iperf bwm-ng top %s" % progs
    print s
    cmd(s)

def monitor_bw(fname="%s/txrate.txt" % default_dir, interval_sec=2):
    """Uses bwm-ng tool to collect iface tx rate stats.  Very reliable."""
    c = "bwm-ng -t %s -o csv -u bits -T rate -C ',' > %s" % (interval_sec * 1000, fname)
    cmd(c)

def monitor_cpu(fname="%s/cpu.txt" % default_dir):
    c = "(top -b -p 1 -d 1 | grep --line-buffered \"^Cpu\") > %s" % fname
    cmd(c)

def monitor_perf(fname="%s/perf.txt" % default_dir, time = 100):
    events = [
        "instructions",
        "cache-misses",
        "branch-instructions",
        "branch-misses",
        "L1-dcache-loads",
        "L1-dcache-load-misses",
        "L1-dcache-stores",
        "L1-dcache-store-misses",
        "L1-dcache-prefetches",
        "L1-dcache-prefetch-misses",
        "L1-icache-loads",
        "L1-icache-load-misses",
        ]
    events = ','.join(events)
    time = int(time)
    c = "(sleep 20; perf stat -e %s -x ' ' -a sleep %d) > %s 2>&1" % (events, time, fname)
    cmd(c)

