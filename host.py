
import paramiko
from subprocess import Popen
import termcolor as T
import os
import socket
from time import sleep

PI_MODULE = '/root/vimal/10g/perfiso_10g_linux/perfiso.ko'
PI_MODULE = '/root/vimal/10g/modules/perfiso.ko'
PI_MODULE = '/root/vimal/exports/perfiso.ko'

host_ips = map(lambda i: "10.0.1.%d" % i, range(1, 21))
host_ips_exclude = ["10.0.1.9", "10.0.1.11", "10.0.1.12", "10.0.1.18"]
for ip in host_ips_exclude:
    host_ips.remove(ip)

def pick_host_ip(i):
    return host_ips[i]

def pick_10g_ip(i):
    return host_ips[i].replace("10.0.1", "192.168.2")

def pick_host_name(i):
    return host_ips[i].replace("10.0.1.", "l")

eth1 = 'eth1'

PI_DEV = {
    3: 'eth3',
    6: 'eth4',
    7: 'eth3',
    10: 'eth6',
    16: eth1,
    17: eth1,

    19: eth1,
    20: eth1,
    }

class HostList(object):
    def __init__(self, *lst):
        self.lst = list(lst)

    def append(self, host):
        self.lst.append(host)

    def __getattribute__(self, name, *args):
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            ret = lambda *args: map(lambda h: h.__getattribute__(name)(*args), self.lst)
            return ret

class Host(object):
    _ssh_cache = {}
    def __init__(self, addr):
        self.addr = addr
        self.tenants = []
        # List of processes spawned async on this host
        self.procs = []
        self.delay = False
        self.delayed_cmds = []
        self.dryrun = False
    def set_dryrun(self, state=True):
        self.dryrun = state

    def get(self):
        ssh = Host._ssh_cache.get(self.addr, None)
        if ssh is None or ssh._transport is None:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.addr, username='root')
            Host._ssh_cache[self.addr] = ssh
        return ssh

    def cmd(self, c, dryrun=False):
        self.log(c)
        if not self.delay:
            if dryrun or self.dryrun:
                return (self.addr, c)
            ssh = self.get()
            out = ssh.exec_command(c)[1].read()
            return out
        else:
            self.delayed_cmds.append(c)
        return (self.addr, c)

    def delayed_cmds_execute(self):
        if len(self.delayed_cmds) == 0:
            return None
        self.delay = False
        ssh = self.get()
        cmds = ';'.join(self.delayed_cmds)
        out = ssh.exec_command(cmds)[1].read()
        self.delayed_cmds = []
        return out

    def cmd_async(self, c, dryrun=False):
        self.log(c)
        if not self.delay:
            if dryrun or self.dryrun:
                return (self.addr, c)
            ssh = self.get()
            out = ssh.exec_command(c)
            return out
        else:
            self.delayed_cmds.append(c)
        return (self.addr, c)

    def delayed_async_cmds_execute(self):
        if len(self.delayed_cmds) == 0:
            return None
        self.delay = False
        ssh = self.get()
        cmds = ';'.join(self.delayed_cmds)
        out = ssh.exec_command(cmds)[1]
        self.delayed_cmds = []
        return out

    def log(self, c):
        addr = T.colored(self.addr, "magenta")
        c = T.colored(c, "grey", attrs=["bold"])
        print "%s: %s" % (addr, c)

    def perfiso_set(self, name, value):
        c = "echo %s > /proc/sys/perfiso/%s" % (value, name)
        self.cmd(c)

    def perfiso_create_txc(self, name):
        c = "echo -n %s > /sys/module/perfiso/parameters/create_txc" % name
        self.cmd(c)

    def perfiso_create_vq(self, name):
        c = "echo -n %s > /sys/module/perfiso/parameters/create_vq" % name
        self.cmd(c)

    def perfiso_assoc_txc_vq(self, txc, vq):
        c = "echo -n associate txc %s vq %s > /sys/module/perfiso/parameters/assoc_txc_vq"
        c = c % (txc, vq)
        self.cmd(c)

    def perfiso_set_vq_weight(self, vq, weight):
        c = "echo -n %s weight %s > /sys/module/perfiso/parameters/set_vq_weight" % (vq, weight)
        self.cmd(c)

    def rmmod(self, mod="perfiso"):
        self.cmd("rmmod %s" % mod)

    def get_10g_dev(self):
        id = int(self.addr.split('.')[-1])
        return PI_DEV.get(id, "eth2")

    def get_10g_ip(self):
        id = int(self.addr.split('.')[-1])
        return "192.168.2.%d" % id

    def get_tenant_ip(self, tid=1):
        assert(tid > 0 and tid < 255)
        myindex = int(self.addr.split('.')[-1])
        return "11.0.%d.%d" % (myindex, tid)

    def insmod(self, mod=PI_MODULE, params="iso_param_dev=eth2"):
        params = "iso_param_dev=%s" % self.get_10g_dev()
        self.cmd("insmod %s %s" % (mod, params))

    def prepare_iface(self, iface=None, ip=None, direct=True):
        if direct:
            # No need for bridge
            dev = self.get_10g_dev()
            self.cmd_async("ifdown %s; ifup %s" % (dev, dev))
            return
        if iface is None:
            iface = self.get_10g_dev()
        if ip is None:
            ip = self.get_10g_ip()
        cmds = ["ifconfig %s 0" % iface,
                "ifconfig br0 down",
                "brctl delbr br0",
                "brctl addbr br0",
                "brctl addif br0 %s" % iface,
                "ifconfig br0 %s up" % (ip)]
        self.cmd('; '.join(cmds))

    def remove_bridge(self, direct=True):
        if direct:
            return
        iface = self.get_10g_dev()
        ip = self.get_10g_ip()
        cmds = ["ifconfig br0 0 down",
                "brctl delbr br0",
                "ifconfig %s %s up" % (iface, ip)]
        self.cmd('; '.join(cmds))

    def remove_qdiscs(self):
        iface = self.get_10g_dev()
        self.cmd("tc qdisc del dev %s root" % iface)

    # Tenant creation/deletion.  IP tenant is the cleanest, and
    # closest to a mac-addr like VM tenant
    def create_ip_tenant(self, tid=1, weight=1, direct=True):
        ip = self.get_tenant_ip(tid)
        self.tenants.append(tid)
        self.delay = True
        self.perfiso_create_txc(ip)
        self.perfiso_create_vq(ip)
        self.perfiso_assoc_txc_vq(ip, ip)
        self.perfiso_set_vq_weight(ip, weight)
        # Configure an alias for the bridge interface
        if direct:
            self.cmd("ifconfig %s:%d %s" % (self.get_10g_dev(), tid, ip))
        else:
            self.cmd("ifconfig br0:%d %s" % (tid, ip))
        self.delayed_cmds_execute()

    def create_tcp_tenant(self, server_ports=[], tid=1, weight=1):
        self.create_service_tenant("tcp", server_ports, tid, weight)

    def create_udp_tenant(self, server_ports=[], tid=1, weight=1):
        self.create_service_tenant("udp", server_ports, tid, weight)

    def create_service_tenant(self, proto="tcp", server_ports=[], tid=1, weight=1):
        # Create tid TX and RX classes
        self.perfiso_create_txc(tid)
        self.perfiso_create_vq(tid)
        self.perfiso_assoc_txc_vq(tid, tid)
        self.perfiso_set_vq_weight(tid, weight)

        # Classify packets out to tid
        for port in server_ports:
            # Server
            ipt = "iptables -A OUTPUT -p %s " % proto
            ipt += " --sport %d -j MARK --set-mark %d" % (port, tid)
            self.cmd(ipt)
            # Client
            ipt = "iptables -A OUTPUT -p %s " % proto
            ipt += " --dport %d -j MARK --set-mark %d" % (port, tid)
            self.cmd(ipt)
            # Server
            ebt = "ebtables -t broute -A BROUTING -p ip --ip-proto %s " % proto
            ebt += " --ip-dport %d --in-if %s " % (port, self.get_10g_dev())
            ebt += " -j mark --set-mark %d" % tid
            self.cmd(ebt)
            ebt = "ebtables -t broute -A BROUTING -p ip --ip-proto %s " % proto
            ebt += " --ip-sport %d --in-if %s " % (port, self.get_10g_dev())
            ebt += " -j mark --set-mark %d" % tid
            self.cmd(ebt)
            # Feedback packets (This needs to be corrected!)
            ebt = "ebtables -t broute -A BROUTING -p ip --ip-proto 143 "
            ebt += "--in-if %s -j mark --set-mark %d " % (self.get_10g_dev(), tid)
            self.cmd(ebt)
        return

    def killall(self, extra=""):
        for p in self.procs:
            try:
                p.kill()
            except:
                pass
        self.cmd("killall -9 ssh iperf top bwm-ng memcached pimonitor %s" % extra)

    def ipt_ebt_flush(self):
        self.cmd("iptables -F; ebtables -t broute -F")

    def remove_tenants(self, direct=True):
        # For iptables/ebtables mark based tenants, use this
        # self.ipt_ebt_flush()
        # This is for IP based tenants
        #for tid in self.tenants:
        dev = "br0"
        if direct:
            dev = self.get_10g_dev()
        filter_cmd = "ifconfig | egrep -o '%s:[0-9]+'" % dev
        self.cmd("for iface in `%s`; do ifconfig $iface down; done" % (filter_cmd))
        self.remove_bridge()

    def configure_rps(self):
        dev = self.get_10g_dev()
        c = "for dir in /sys/class/net/%s/queues/rx*; do "
        c += " echo e > $dir/rps_cpus; done"
        self.cmd(c % dev)

    # Monitoring scripts
    def start_cpu_monitor(self, dir="/tmp"):
        dir = os.path.abspath(dir)
        path = os.path.join(dir, "cpu.txt")
        self.cmd("mkdir -p %s" % dir)
        cmd = "(top -b -p1 -d1 | grep --line-buffered \"^Cpu\") > %s" % path
        return self.cmd_async(cmd)

    def start_bw_monitor(self, dir="/tmp", interval_sec=2):
        dir = os.path.abspath(dir)
        path = os.path.join(dir, "net.txt")
        self.cmd("mkdir -p %s" % dir)
        cmd = "bwm-ng -t %s -o csv -u bits -T rate -C ',' > %s" % (interval_sec * 1000, path)
        return self.cmd_async(cmd)

    def start_tenant_monitor(self, dir="/tmp"):
        dir = os.path.abspath(dir)
        path = os.path.join(dir, "tenant.txt")
        cmd = "~/vimal/exports/pimonitor > %s" % path
        return self.cmd_async(cmd)

    def start_perf_monitor(self, dir="/tmp", time=30):
        dir = os.path.abspath(dir)
        path = os.path.join(dir, "perf.txt")
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
        # This command will use debug counters, so you can't run it when
        # running oprofile
        events = ','.join(events)
        cmd = "(perf stat -e %s -a sleep %d) > %s 2>&1" % (events, time, path)
        return self.cmd_async(cmd)

    def start_monitors(self, dir="/tmp"):
        return [self.start_cpu_monitor(dir),
                self.start_bw_monitor(dir),
                self.start_tenant_monitor(dir)]

    def copy(self, dest="l1", dir="/tmp", exptid=None):
        dir = os.path.abspath(dir)
        # This name usually contains the parameters
        expt = os.path.basename(dir)
        if dir == "/tmp" or exptid is None:
            return
        if type(dest) == str:
            dest = Host(dest)
        src_path = dir
        dst_path = "~/vimal/10g/exptdata/%s/%s/%s/" % (exptid, expt, self.hostname())
        dest.cmd("mkdir -p %s" % dst_path)
        opts = "-o StrictHostKeyChecking=no"
        c = "scp %s -r %s/* %s:%s" % (opts, src_path, dest.hostname(), dst_path)
        self.cmd(c)

    def hostname(self):
        return socket.gethostbyaddr(self.addr)[0]

    def start_profile(self, dir="/tmp"):
        dir = os.path.join(os.path.abspath(dir), "profile")
        c = "mkdir -p %s; export SESSION_DIR=%s;" % (dir, dir)
        c += "opcontrol --reset; opcontrol --start-daemon; opcontrol --start;"
        self.cmd(c)

    def stop_profile(self, dir="/tmp"):
        dir = os.path.join(os.path.abspath(dir), "profile")
        c = "export SESSION_DIR=%s; opcontrol --stop; opcontrol --dump;" % dir
        c += "opcontrol --save profile;"
        c += "opcontrol --deinit; killall -9 oprofiled; opcontrol --deinit;"
        self.cmd(c)

    def start_memcached(self):
        self.stop_memcached()
        c = "ulimit -n unlimited; memcached -t 8 -b 10241024 -m 8192 -v -c 1024000 -u nobody"
        proc = self.cmd_async(c)
        self.procs.append(proc)
        return proc

    def stop_memcached(self):
        self.cmd("killall -9 memcached")

    def disable_syncookies(self):
        self.cmd("sysctl -w net.ipv4.tcp_syncookies=0")

    def set_mtu(self, mtu):
        dev = self.get_10g_dev()
        self.cmd("ifconfig %s mtu %s" % (dev, mtu))
