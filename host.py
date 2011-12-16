
import paramiko
from subprocess import Popen
import termcolor as T

PI_MODULE = '/root/vimal/10g/perfiso_10g_linux/perfiso.ko'
PI_MODULE = '/root/vimal/10g/modules/perfiso.ko'

eth1 = 'eth1'

PI_DEV = {
    3: 'eth3',
    6: 'eth4',
    7: 'eth3',
    16: eth1,
    17: eth1,

    19: eth1,
    20: eth1,
    }

class HostList(object):
    def __init__(self, *lst):
        self.lst = lst

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

    def get(self):
        ssh = Host._ssh_cache.get(self.addr, None)
        if ssh is None or ssh._transport is None:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.addr, username='root')
            Host._ssh_cache[self.addr] = ssh
        return ssh

    def cmd(self, c):
        ssh = self.get()
        self.log(c)
        out = ssh.exec_command(c)[1].read()
        return out

    def cmd_async(self, c):
        ssh = self.get()
        self.log(c)
        out = ssh.exec_command(c)
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
        c = "echo -n %s weight %d > /sys/module/perfiso/parameters/set_vq_weight" % (vq, weight)
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

    def prepare_iface(self, iface=None, ip=None):
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

    def remove_bridge(self):
        iface = self.get_10g_dev()
        ip = self.get_10g_ip()
        cmds = ["ifconfig br0 0 down",
                "brctl delbr br0",
                "ifconfig %s %s up" % (iface, ip)]
        self.cmd('; '.join(cmds))

    def create_ip_tenant(self, tid=1, weight=1):
        ip = self.get_tenant_ip(tid)
        self.tenants.append(tid)
        self.perfiso_create_txc(ip)
        self.perfiso_create_vq(ip)
        self.perfiso_assoc_txc_vq(ip, ip)
        self.perfiso_set_vq_weight(ip, weight)
        # Configure an alias for the bridge interface
        dev = self.get_10g_dev()
        self.cmd("ifconfig br0:%d %s" % (tid, self.get_tenant_ip(tid)))

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

    def start_cpu_monitor(self, dir="/tmp"):
        pass

    def start_bw_monitor(self, dir="/tmp"):
        pass

    def killall(self):
        self.cmd("killall -9 ssh iperf top bwm-ng")

    def ipt_ebt_flush(self):
        self.cmd("iptables -F; ebtables -t broute -F")

    def remove_tenants(self):
        # For iptables/ebtables mark based tenants, use this
        # self.ipt_ebt_flush()
        # This is for IP based tenants
        for tid in self.tenants:
            self.cmd("ifconfig br0:%d down" % tid)

    def configure_rps(self):
        dev = self.get_10g_dev()
        c = "for dir in /sys/class/net/%s/queues/rx*; do "
        c += " echo e > $dir/rps_cpus; done"
        self.cmd(c % dev)
