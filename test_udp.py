from expt import Expt
from host import *
from iperf import Iperf

class Udp(Expt):
    def __init__(self, **kwargs):
        Expt.__init__(self, kwargs)
        self.desc = """Just test the rate limiter for UDP"""

    def start(self):
        h1 = Host("10.0.1.1")
        h2 = Host("10.0.1.2")
        h3 = Host("10.0.1.3")
        dev="eth2"
        self.hlist = HostList(h1, h2, h3)
        hlist = self.hlist

        h1.prepare_iface()
        h2.prepare_iface()
        h3.prepare_iface()

        hlist.rmmod()
        hlist.ipt_ebt_flush()
        if self.opts("enabled"):
            hlist.insmod()
            self.log("Creating a single UDP tenant")
            h1.create_udp_tenant(server_ports=[5001], tid=1)
            h1.create_udp_tenant(server_ports=[5002], tid=1)

            h2.create_udp_tenant(server_ports=[5001], tid=1)
            h3.create_udp_tenant(server_ports=[5002], tid=1)
            h1.perfiso_set("IsoAutoGenerateFeedback", "1")
            h1.perfiso_set("ISO_FEEDBACK_INTERVAL_US", 100)
            h1.perfiso_set("ISO_VQ_DRAIN_RATE_MBPS", 5000)
            #hlist.perfiso_set("ISO_VQ_MAX_BYTES", 50 * 1024)
            #hlist.perfiso_set("ISO_MAX_BURST_TIME_US", 500)
            #hlist.perfiso_set("ISO_VQ_MARK_THRESH_BYTES", 25 * 1024)

        hlist.start_monitors(self.opts("dir"))

        self.procs = []
        # Start iperf servers
        for p in [5001, 5002]:
            opts = {'-p': p, '-u': True}
            iperf = Iperf(opts)
            server = iperf.start_server(h1)
            self.procs.append(server)

        # Start 32 UDP from h2 to h1
        client = Iperf({'-p': 5001,
                        '-c': h1.get_10g_ip(),
                        '-t': self.opts("t"),
                        '-b': '3G',
                        '-P': 32})
        client = client.start_client(h2)
        self.procs.append(client)

        # Start 32 UDP from h3 to h1
        client = Iperf({'-p': 5002,
                        '-c': h1.get_10g_ip(),
                        '-t': self.opts("t"),
                        '-b': '3G',
                        '-P': 32})
        client = client.start_client(h3)
        self.procs.append(client)

    def stop(self):
        self.hlist.copy("l1", self.opts("dir"))
        for p in self.procs:
            p.kill()
        self.hlist.killall()
