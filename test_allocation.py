from expt import Expt
from host import *
from iperf import Iperf
from time import sleep
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('--dir',
                        required=True,
                        dest="dir")

    parser.add_argument('--time', '-t',
                        type=int,
                        dest="t",
                        help="Time to run expt",
                        default=30)

    parser.add_argument('-n',
                        type=int,
                        dest="n",
                        help="Number of tenants per host",
                        default=3)

    parser.add_argument('--vqrate',
                        dest="vqrate",
                        help="VQ drain rate.",
                        default="9000")

    parser.add_argument('--exptid',
                        dest="exptid",
                        help="Experiment ID",
                        default=None)

    parser.add_argument('--topo',
                        dest="topo",
                        help="Topology",
                        default=1,
                        type=int)

    args = parser.parse_args()

class Allocation(Expt):
    def start(self):
        h1 = Host("10.0.1.1")
        h2 = Host("10.0.1.2")
        h3 = Host("10.0.1.3")
        h4 = Host("10.0.1.4")

        if self.opts("topo") == 1:
            self.hlist = HostList(h1, h2)
        else:
            self.hlist = HostList(h1, h2, h3, h4)
        hlist = self.hlist

        hlist.prepare_iface()
        hlist.rmmod()
        hlist.insmod()
        for tid in xrange(self.opts("n")):
            hlist.create_ip_tenant(tid+1)

        hlist.perfiso_set("ISO_VQ_DRAIN_RATE_MBPS", self.opts("vqrate"))
        hlist.perfiso_set("ISO_MAX_TX_RATE", self.opts("vqrate"))
        hlist.start_monitors(self.opts("dir"), 1e6)

        if self.opts("topo") == 1:
            h2.cmd_async("iperf -s")
            sleep(1)
            #hlist.setup_tenant_routes(self.opts("n"))

            for tid in xrange(self.opts("n")-1):
                client = Iperf({'-c': h2.get_tenant_ip(tid+1),
                                '-t': self.opts("t"),
                                '-B': h1.get_tenant_ip(1),
                                '-P': 2})
                client.start_client(h1)

            for tid in xrange(1, self.opts("n")):
                client = Iperf({'-c': h2.get_tenant_ip(self.opts("n")),
                                '-t': self.opts("t"),
                                '-B': h1.get_tenant_ip(tid+1),
                                '-P': 2})
                client.start_client(h1)
        else:
            h3.cmd_async("iperf -s")
            h4.cmd_async("iperf -s")

            n = self.opts("n") - 2
            for tid in xrange(n):
                client = Iperf({'-c': h3.get_tenant_ip(tid+1),
                                '-t': self.opts("t"),
                                '-B': h1.get_tenant_ip(1),
                                '-P': 2})
                client.start_client(h1)

            client = Iperf({'-c': h4.get_tenant_ip(1),
                            '-t': self.opts("t"),
                            '-B': h1.get_tenant_ip(1),
                            '-P': 2})
            client.start_client(h1)

            # Second tenant
            client = Iperf({'-c': h4.get_tenant_ip(2),
                            '-t': self.opts("t"),
                            '-B': h1.get_tenant_ip(2),
                            '-P': 2})
            client.start_client(h1)

            for tid in xrange(n):
                client = Iperf({'-c': h4.get_tenant_ip(2),
                                '-t': self.opts("t"),
                                '-B': h2.get_tenant_ip(tid+1),
                                '-P': 2})
                client.start_client(h2)


    def stop(self):
        self.hlist.remove_tenants()
        self.hlist.copy("l1", self.opts("dir"), self.opts("exptid"))
        self.hlist.killall("iperf")

if __name__ == "__main__":
    Allocation(vars(args)).run()

