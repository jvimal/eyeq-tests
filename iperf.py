
from host import Host
import common

class Iperf:
    def __init__(self, opts):
        self.opts = opts

    def start_server(self, host, cpu=None):
        cmd = "iperf -s -p %d" % (self.opts.get('-p', 5001))
        if self.opts.get('-u', False):
            cmd += " -u -l32k"
        if self.opts.get('-B', False):
            cmd += " -B %s " % self.opts.get('-B')
        if cpu is not None:
            cpu = cpu % 8
            cmd = "taskset -c %d %s" % (cpu, cmd)
        host.cmd_async(cmd)
        return self

    def start_client(self, host, cpu=None):
        server_ip = self.opts.get('-c', '')
        port = self.opts.get('-p', '')
        parallel = self.opts.get('-P', '')
        t = self.opts.get('-t', 30)
        cmd = "iperf -c %s -P %s -t %d" % (server_ip, parallel, t)
        if self.opts.get('-b', False): # -b implies UDP, which is weird
            cmd += " -b %s -l32k" % self.opts.get('-b')
        if self.opts.get('-B', False):
            cmd += " -B %s " % self.opts.get('-B')
        cmd += " > /tmp/iperf-%s 2>&1" % server_ip
        if cpu is not None:
            cpu = cpu % 8
            cmd = "taskset -c %d %s" % (cpu, cmd)
        if self.opts.get('start_udp', None):
            cmd = "sleep %s; " % self.opts.get('start_udp') + cmd
        host.cmd_async(cmd)
        return self

    def kill(self):
        pass
