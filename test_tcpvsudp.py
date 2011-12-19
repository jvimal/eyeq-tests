from expt import Expt
from host import *
from iperf import Iperf
from time import sleep

class TcpVsUdp(Expt):
    def __init__(self, **kwargs):
        Expt.__init__(self, kwargs)
        self.desc = """Test fairness between 1 TCP and 32 UDP sessions"""

    def start(self):
        h1 = Host("10.0.1.1")
        h2 = Host("10.0.1.2")
        hlist = HostList(h1, h2)
        hlist_udp = HostList()
        for i in xrange(3, 3+self.opts("n")+1):
            hi = Host("10.0.1.%d" % i)
            hlist.append(hi)
            hlist_udp.append(hi)

        self.hlist = hlist

        if self.opts("enabled"):
            hlist.prepare_iface()
        else:
            hlist.remove_bridge()

        hlist.rmmod()
        hlist.ipt_ebt_flush()
        if self.opts("enabled"):
            hlist.insmod()
            self.log("Creating two tenants")
            #h1.create_tcp_tenant(server_ports=[5001], tid=1)
            #h1.create_udp_tenant(server_ports=[5002], tid=2)

            #h2.create_tcp_tenant(server_ports=[5001], tid=1)
            #h3.create_udp_tenant(server_ports=[5002], tid=2)
            h1.create_ip_tenant(tid=1)
            h1.create_ip_tenant(tid=2)

            h2.create_ip_tenant(tid=1)
            for hi in hlist_udp.lst:
                hi.create_ip_tenant(tid=1)

        if self.opts("enabled"):
            hlist.perfiso_set("IsoAutoGenerateFeedback", "1")
            hlist.perfiso_set("ISO_VQ_DRAIN_RATE_MBPS", 8700)
            hlist.perfiso_set("ISO_VQ_UPDATE_INTERVAL_US", 25)
        hlist.start_monitors(self.opts("dir"))

        self.procs = []
        # Start iperf servers
        iperf = Iperf({'-p': 5001})
        server = iperf.start_server(h1.addr)
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
        client = client.start_client(h2.addr)
        self.procs.append(client)

        for hi in hlist_udp.lst:
            # Start 32 UDP from h3 to h1
            opts = {'-p': 5002,
                    '-c': h1.get_10g_ip(),
                    '-t': self.opts("t"),
                    '-b': '3G',
                    '-P': self.opts("P")}
            if self.opts("enabled"):
                opts['-c'] = h1.get_tenant_ip(2)
            client = Iperf(opts)
            client = client.start_client(hi.addr)
            self.procs.append(client)

    def stop(self):
        self.hlist.remove_tenants()
        self.hlist.copy("l1", self.opts("dir"))
        for p in self.procs:
            p.kill()
        self.hlist.killall()
