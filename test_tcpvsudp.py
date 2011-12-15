from expt import Expt
from host import *
from iperf import Iperf

class TcpVsUdp(Expt):
    def __init__(self, **kwargs):
        Expt.__init__(self, kwargs)
        self.desc = """Test fairness between 1 TCP and 32 UDP sessions"""

    def start(self):
        h1 = Host("10.0.1.1")
        h2 = Host("10.0.1.2")
        h3 = Host("10.0.1.3")
        self.hlist = HostList(h1, h2, h3)
        hlist = self.hlist

        if self.opts("enabled"):
            hlist.prepare_iface()
        else:
            hlist.remove_bridge()

        hlist.rmmod()
        hlist.ipt_ebt_flush()
        if self.opts("enabled"):
            hlist.insmod()
            self.log("Creating two tenants")
            h1.create_tcp_tenant(server_ports=[5001], tid=1)
            h1.create_udp_tenant(server_ports=[5002], tid=2)

            h2.create_tcp_tenant(server_ports=[5001], tid=1)
            h3.create_udp_tenant(server_ports=[5002], tid=2)
            h1.perfiso_set("IsoAutoGenerateFeedback", "1")

        hlist.start_cpu_monitor()
        hlist.start_bw_monitor()

        self.procs = []
        # Start iperf servers
        for p in [5001, 5002]:
            opts = {'-p': p}
            if p == 5002:
                opts['-u'] = True
            iperf = Iperf(opts)
            server = iperf.start_server(h1.get_10g_ip())
            self.procs.append(server)

        # Start 1 TCP connection from h2 to h1
        client = Iperf({'-p': 5001,
                        '-c': h1.get_10g_ip(),
                        '-t': self.opts("t"),
                        '-P': 1})
        client = client.start_client(h2.get_10g_ip())
        self.procs.append(client)

        # Start 32 UDP from h3 to h1
        client = Iperf({'-p': 5002,
                        '-c': h1.get_10g_ip(),
                        '-t': self.opts("t"),
                        '-b': '3G',
                        '-P': self.opts("P")})
        client = client.start_client(h3.get_10g_ip())
        self.procs.append(client)

    def stop(self):
        for p in self.procs:
            p.kill()
        self.hlist.killall()
