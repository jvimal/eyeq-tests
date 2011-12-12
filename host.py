
import paramiko
from subprocess import Popen
import termcolor as T

PI_MODULE = '/root/vimal/10g/perfiso_10g_linux/perfiso.ko'
PI_DEV = 'eth2'

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

    def rmmod(self, mod="perfiso"):
        self.cmd("rmmod %s" % mod)

    def insmod(self, mod=PI_MODULE, params="iso_param_dev=eth2"):
        self.cmd("insmod %s %s" % (mod, params))

    def prepare_iface(self, iface, ip):
        cmds = ["ifconfig %s 0" % iface,
                "brctl addbr br0",
                "brctl addif br0 %s" % iface,
                "ifconfig br0 %s up" % (ip)]
        self.cmd('; '.join(cmds))

