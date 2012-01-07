from expt import Expt
from host import *
from iperf import Iperf
from time import sleep
import subprocess

class TcpVsUdp(Expt):
    def __init__(self, **kwargs):
        Expt.__init__(self, kwargs)
        self.desc = """Test fairness between 1 TCP and UDP on multiple hosts"""
        if self.opts("traffic") and not os.path.exists(self.opts("traffic")):
            raise "File %s not found" % self.opts("traffic")

    def start(self):
        h1 = Host("10.0.1.1")
        h2 = Host("10.0.1.2")
        hlist = HostList(h1, h2)
        hlist_udp = HostList()
        for i in xrange(2, 2+self.opts("n")):
            ip = pick_host_ip(i)
            hi = Host(ip)
            hlist.append(hi)
            hlist_udp.append(hi)

        self.hlist = hlist

        if self.opts("enabled"):
            hlist.prepare_iface()
        else:
            hlist.remove_bridge()

        hlist.rmmod()
        if self.opts("enabled"):
            hlist.insmod()
            self.log("Creating two tenants")
            #h1.create_tcp_tenant(server_ports=[5001], tid=1)
            #h1.create_udp_tenant(server_ports=[5002], tid=2)

            #h2.create_tcp_tenant(server_ports=[5001], tid=1)
            #h3.create_udp_tenant(server_ports=[5002], tid=2)
            h1.create_ip_tenant(tid=1)
            h1.create_ip_tenant(tid=2)
            # Set the weight for TCP tenant.  UDP's weight is 1
            h1.perfiso_set_vq_weight(vq=1, weight=self.opts("wtcp"))

            h2.create_ip_tenant(tid=1)
            #for hi in hlist_udp.lst:
            #    hi.create_ip_tenant(tid=2)
            hlist_udp.create_ip_tenant(2)

        if self.opts("enabled"):
            hlist.perfiso_set("IsoAutoGenerateFeedback", "1")
            hlist.perfiso_set("ISO_VQ_DRAIN_RATE_MBPS", 8500)
            hlist.perfiso_set("ISO_VQ_UPDATE_INTERVAL_US", 25)
            hlist.perfiso_set("ISO_RFAIR_INITIAL", 9000)
        if self.opts("mtu"):
            hlist.set_mtu(self.opts("mtu"))
        else:
            hlist.set_mtu("1500")
        hlist.start_monitors(self.opts("dir"))

        self.procs = []
        # Start iperf servers
        iperf = Iperf({'-p': 5001})
        server = iperf.start_server(h1)
        self.procs.append(server)

        sleep(1)
        # Start 1 TCP connection from h2 to h1
        opts = {'-p': 5001,
                '-c': h1.get_10g_ip(),
                '-t': self.opts("t"),
                'dir': self.opts("dir"),
                '-P': 1}
        if self.opts("enabled"):
            opts['-c'] = h1.get_tenant_ip(1)
        client = Iperf(opts)
        client = client.start_client(h2)
        self.procs.append(client)

        if self.opts("traffic"):
            for hi in hlist.lst:
                LOADGEN = "taskset -c 7 /root/vimal/exports/loadgen"
                if self.opts("enabled"):
                    ip = hi.get_tenant_ip(2)
                else:
                    ip = hi.get_10g_ip()
                out = os.path.join(self.opts("dir"), "loadgen.txt")
                cmd = "%s -i %s " % (LOADGEN, ip)
                cmd += "-l 12345 -p 500000 -f %s > %s" % (self.opts("traffic"), out)
                hi.cmd_async(cmd)
            # Start it
            sleep(5)
            execs = []
            for hi in hlist.lst:
                if self.opts("enabled"):
                    ip = hi.get_tenant_ip(2)
                else:
                    ip = hi.get_10g_ip()
                execs.append(subprocess.Popen("nc -nzv %s %s" % (ip, 12345), shell=True))
            for e in execs:
                e.wait()
        else:
            for hi in hlist_udp.lst:
                # Start 32 UDP from h3 to h1
                opts = {'-p': 5002,
                        '-c': h1.get_10g_ip(),
                        '-t': self.opts("t"),
                        '-b': '3G',
                        'start_udp': self.opts("start_udp"),
                        '-B': hi.get_tenant_ip(2),
                        '-P': self.opts("P")}
                if self.opts("enabled"):
                    opts['-c'] = h1.get_tenant_ip(2)
                client = Iperf(opts)
                client = client.start_client(hi)
                self.procs.append(client)

    def stop(self):
        self.hlist.set_mtu("1500")
        self.hlist.killall("loadgen")
        self.hlist.remove_tenants()
        self.hlist.copy("l1", self.opts("dir"))
        for p in self.procs:
            p.kill()
