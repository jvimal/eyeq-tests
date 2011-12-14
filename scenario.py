#!/usr/bin/python
import sys
import argparse
import multiprocessing
from common import *
import termcolor as T
from expt import Expt
from iperf import Iperf
from time import sleep
from host import *

parser = argparse.ArgumentParser(description="Perfiso simple scenarios testing.")
parser.add_argument('--test',
                    dest="test",
                    type=int,
                    help="Test number to conduct.")

parser.add_argument('--list', '-l',
                    dest="lst",
                    action="store_true",
                    default=False)

parser.add_argument('--dir',
                    dest="dir",
                    required=True)

parser.add_argument('--enabled',
                    dest="enabled",
                    help="Enable perfisolation",
                    default=False)

args = parser.parse_args()

class Tcp2Vs32(Expt):
    def __init__(self, **kwargs):
        Expt.__init__(self, kwargs)
        self.desc = """Test fairness between 1 TCP and 32 TCP connections"""

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
            self.log("Creating two tenants")
            h1.create_tcp_tenant(server_ports=[5001], tid=1)
            h1.create_tcp_tenant(server_ports=[5002], tid=1)

            h2.create_tcp_tenant(server_ports=[5001], tid=1)
            h3.create_tcp_tenant(server_ports=[5002], tid=1)

        hlist.start_cpu_monitor()
        hlist.start_bw_monitor()

        self.procs = []
        # Start iperf servers
        for p in [5001, 5002]:
            iperf = Iperf({'-p': p,
                           '-c': h1.get_10g_ip()})
            server = iperf.start_server(h1.get_10g_ip())
            self.procs.append(server)

        # Start 1 TCP connection from h2 to h1
        client = Iperf({'-p': 5001,
                        '-c': h1.get_10g_ip(),
                        '-P': 1})
        client = client.start_client(h2.get_10g_ip())
        self.procs.append(client)

        # Start 32 TCP from h3 to h1
        client = Iperf({'-p': 5002,
                        '-c': h1.get_10g_ip(),
                        '-P': 32})
        client = client.start_client(h3.get_10g_ip())
        self.procs.append(client)

    def stop(self):
        for p in self.procs:
            p.kill()
        self.hlist.killall()

Tcp2Vs32(t=240, enabled=args.enabled).run()
