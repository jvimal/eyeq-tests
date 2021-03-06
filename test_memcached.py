from expt import Expt
from host import *
from iperf import *
from time import sleep
import os

class Memcached(Expt):
    def __init__(self, **kwargs):
        Expt.__init__(self, kwargs)
        self.desc = "Memcached experiments"

    def start(self):
        h1 = Host("10.0.1.17")
        h2 = Host("10.0.1.19")
        h3 = Host("10.0.1.20")
        hlist = HostList(h1, h2, h3)

        hlist.cmd("killall -9 memaslap")
        hlist.cmd("sysctl -w net.ipv4.tcp_delayed_ack=1")
        hlist.rmmod()
        dir = self.opts("dir")
        self.hlist = hlist
        # h2 to h1 memcached
        # h3 to h1 iperf tcp

        # just memcached, for bare-metal run
        if self.opts("case") == 1:
            self.case1()
        # just memcached + bridge additional latency
        elif self.opts("case") == 2:
            self.case2()
        # just memcached + perfiso
        elif self.opts("case") == 3:
            self.case3()
        # memcached + cross traffic (udp) without perfiso
        elif self.opts("case") == 4:
            self.case4()
        # memcached + cross traffic (udp) with perfiso
        elif self.opts("case") == 5:
            self.case5()
        elif self.opts("case") == 6:
            self.case6()

    def case1(self, out="case1"):
        h1 = Host("10.0.1.17")
        h2 = Host("10.0.1.19")
        hlist = HostList(h1, h2)
        h1.start_memcached()
        hlist.configure_rps()
        hlist.disable_syncookies()

        dir = os.path.join(self.opts("dir"), out)
        cmd = "mkdir -p %s; " % dir
        #cmd += "cd ~/vimal/libmemcached-1.0.2/clients; "
        time = int(self.opts("t")) - 10
        cmd += "memaslap -s %s:11211 -S 1s -t %ss -c 512 -T 8 -B -F ~/vimal/exports/memaslap.cnf" % (h1.get_10g_ip(), time)
        cmd += " > %s" % (os.path.join(dir, "memaslap.txt"))
        h2.cmd_async(cmd)
        hlist.start_monitors(dir)

    def case2(self, insert=False, out="case2"):
        h1 = Host("10.0.1.17")
        h2 = Host("10.0.1.19")
        hlist = HostList(h1, h2)
        hlist.rmmod()
        if insert:
            hlist.insmod()
            hlist.perfiso_set("ISO_RFAIR_INITIAL", 20000)
            hlist.perfiso_set("ISO_VQ_DRAIN_RATE_MBPS", 20000)
        hlist.prepare_iface()
        hlist.configure_rps()
        hlist.disable_syncookies()

        h1.start_memcached()
        hlist.create_ip_tenant(1)

        dir = os.path.join(self.opts("dir"), out)
        cmd = "mkdir -p %s; " % dir
        #cmd += "cd ~/vimal/libmemcached-1.0.2/clients; "
        time = int(self.opts("t")) - 10
        cmd += "memaslap -s %s:11211 -S 1s -t %ss -c 512 -T 8 -B -F ~/vimal/exports/memaslap.cnf" % (h1.get_tenant_ip(1), time)
        cmd += " > %s" % (os.path.join(dir, "memaslap.txt"))
        h2.cmd_async(cmd)
        hlist.start_monitors(dir)

    def case3(self):
        self.case2(insert=True, out="case3")

    def case4(self, out="case4", static=False):
        self.case1(out=out)
        h1 = Host("10.0.1.17")
        h3 = Host("10.0.1.20")
        if static:
            h3.create_ip_tx_rl(ip=h3.get_10g_ip(), rate='4Gbit', static=True)
        iperf = Iperf({'-c': h1.get_10g_ip(),
                       '-t': self.opts("t"),
                       '-P': 16,
                       '-b': '3G',
                       '-u': True})
        self.procs.append(iperf.start_server(h1))
        self.procs.append(iperf.start_client(h3))

    def case5(self):
        self.case2(insert=True, out="case5")
        self.hlist.perfiso_set("IsoAutoGenerateFeedback", 1)
        self.hlist.perfiso_set("ISO_RFAIR_INITIAL", 1000)
        self.hlist.perfiso_set("ISO_VQ_DRAIN_RATE_MBPS", 8500)
        self.hlist.perfiso_set("ISO_VQ_UPDATE_INTERVAL_US", 25)
        h1 = Host("10.0.1.17")
        h2 = Host("10.0.1.19")
        h3 = Host("10.0.1.20")
        h3.rmmod()
        h3.insmod()
        h3.prepare_iface()
        h3.configure_rps()
        h3.disable_syncookies()

        HostList(h1, h3).create_ip_tenant(2)
        iperf = Iperf({'-c': h1.get_tenant_ip(2),
                       '-B': h3.get_tenant_ip(2),
                       '-t': self.opts("t"),
                       '-P': 16,
                       '-b': '3G',
                       '-u': True})
        self.procs.append(iperf.start_server(h1))
        self.procs.append(iperf.start_client(h3))

    def case6(self):
        # Without iso, but with static allocation
        # Goal: to compare how good we're against static allocation
        self.case4(out="case6", static=True)

    def stop(self):
        for p in self.procs:
            p.kill()
        self.hlist.remove_qdiscs()
        self.hlist.killall()
        self.hlist.remove_tenants()
