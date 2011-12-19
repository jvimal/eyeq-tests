from expt import Expt
from host import *
from iperf import Iperf
from time import sleep

class Tcp2Vs32(Expt):
    def __init__(self, **kwargs):
        Expt.__init__(self, kwargs)
        self.desc = """Test fairness between 1 TCP and 32 TCP connections"""

    def start(self):
        h1 = Host("10.0.1.1")
        h2 = Host("10.0.1.2")
        h3 = Host("10.0.1.3")
        self.hlist = HostList(h1, h2, h3)
        hlist = self.hlist

        hlist.prepare_iface()
        hlist.configure_rps()
        hlist.rmmod()
        hlist.ipt_ebt_flush()
        if self.opts("enabled"):
            hlist.insmod()
            self.log("Creating two tenants")
            #h1.create_tcp_tenant(server_ports=[5001], tid=1)
            #h1.create_tcp_tenant(server_ports=[5002], tid=2)
            #h2.create_tcp_tenant(server_ports=[5001], tid=1)
            #h3.create_tcp_tenant(server_ports=[5002], tid=2)
            h1.create_ip_tenant(tid=1)
            h1.create_ip_tenant(tid=2)

            h2.create_ip_tenant(tid=1)
            h3.create_ip_tenant(tid=1)

        if self.opts("enabled"):
            hlist.perfiso_set("ISO_VQ_DRAIN_RATE_MBPS", 8700)
            hlist.perfiso_set("IsoAutoGenerateFeedback", 1)
            hlist.perfiso_set("ISO_VQ_UPDATE_INTERVAL_US", 25)
        hlist.start_monitors(self.opts("dir"))

        self.procs = []
        # Start iperf servers
        for p in [5001, 5002]:
            iperf = Iperf({'-p': p})
            server = iperf.start_server(h1.addr)
            self.procs.append(server)

        sleep(1)
        # Start 1 TCP connection from h2 to h1
        client = Iperf({'-p': 5001,
                        '-c': h1.get_10g_ip(),
                        '-t': self.opts("t"),
                        '-P': 1})
        if self.opts("enabled"):
            client.opts["-c"] = h1.get_tenant_ip(1)
        client = client.start_client(h2.addr)
        self.procs.append(client)

        # Start 32 TCP from h3 to h1
        client = Iperf({'-p': 5002,
                        '-c': h1.get_10g_ip(),
                        '-t': self.opts("t"),
                        '-P': 32})
        if self.opts("enabled"):
            client.opts["-c"] = h1.get_tenant_ip(2)
        client = client.start_client(h3.addr)
        self.procs.append(client)

    def stop(self):
        self.hlist.remove_tenants()
        self.hlist.copy("l1", self.opts("dir"))
        for p in self.procs:
            p.kill()
        self.hlist.killall()
