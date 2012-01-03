from expt import Expt
from host import *
from iperf import Iperf
from time import sleep

class TcpVsUdp(Expt):
    def __init__(self, **kwargs):
        Expt.__init__(self, kwargs)
        self.desc = """Test fairness between 1 TCP and UDP on multiple hosts"""

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
            for hi in hlist_udp.lst:
                hi.create_ip_tenant(tid=1)

        if self.opts("enabled"):
            hlist.perfiso_set("IsoAutoGenerateFeedback", "1")
            hlist.perfiso_set("ISO_VQ_DRAIN_RATE_MBPS", 8500)
            hlist.perfiso_set("ISO_VQ_UPDATE_INTERVAL_US", 25)
            hlist.perfiso_set("ISO_RFAIR_INITIAL", 9000)
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
                '-P': 1}
        if self.opts("enabled"):
            opts['-c'] = h1.get_tenant_ip(1)
        client = Iperf(opts)
        client = client.start_client(h2)
        self.procs.append(client)

        for hi in hlist_udp.lst:
            # Start 32 UDP from h3 to h1
            opts = {'-p': 5002,
                    '-c': h1.get_10g_ip(),
                    '-t': self.opts("t"),
                    '-b': '3G',
                    'start_udp': self.opts("start_udp"),
                    '-P': self.opts("P")}
            if self.opts("enabled"):
                opts['-c'] = h1.get_tenant_ip(2)
            client = Iperf(opts)
            client = client.start_client(hi)
            self.procs.append(client)

    def stop(self):
        self.hlist.killall()
        self.hlist.remove_tenants()
        self.hlist.copy("l1", self.opts("dir"))
        for p in self.procs:
            p.kill()
