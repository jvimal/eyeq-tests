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
        # just memcached + bridge + perfiso
        elif self.opts("case") == 3:
            self.case3()
        # memcached + cross traffic (udp) without perfiso
        elif self.opts("case") == 4:
            self.case4()
        # memcached + cross traffic (udp) with perfiso
        elif self.opts("case") == 5:
            self.case5()

    def case1(self, out="case1"):
        h1 = Host("10.0.1.17")
        h2 = Host("10.0.1.19")
        hlist = HostList(h1, h2)
        h1.start_memcached()
        hlist.configure_rps()
        hlist.disable_syncookies()

        dir = os.path.join(self.opts("dir"), out)
        cmd = "mkdir -p %s; " % dir
        cmd += "cd ~/vimal/libmemcached-1.0.2/clients; "
        time = int(self.opts("t")) - 5
        cmd += "./memaslap -s %s:11211 -S 1s -t %ss -n 4 -c 128 -T 8 -B -F ~/vimal/exports/memaslap.cnf" % (h1.get_10g_ip(), time)
        cmd += " > %s" % (os.path.join(dir, "memaslap.txt"))
        h2.cmd_async(cmd)
        h2.start_monitors(dir)

    def case2(self, insert=False, out="case2"):
        h1 = Host("10.0.1.17")
        h2 = Host("10.0.1.19")
        hlist = HostList(h1, h2)
        hlist.rmmod()
        if insert:
            hlist.insmod()
            hlist.perfiso_set("ISO_RFAIR_INITIAL", 11000)
            hlist.perfiso_set("ISO_VQ_DRAIN_RATE_MBPS", 11000)
        hlist.prepare_iface()
        hlist.configure_rps()
        hlist.disable_syncookies()

        h1.start_memcached()
        hlist.create_ip_tenant(1)

        dir = os.path.join(self.opts("dir"), out)
        cmd = "mkdir -p %s; " % dir
        cmd += "cd ~/vimal/libmemcached-1.0.2/clients; "
        time = int(self.opts("t")) - 5
        cmd += "./memaslap -s %s:11211 -S 1s -t %ss -n 4 -c 128 -T 8 -B -F ~/vimal/exports/memaslap.cnf" % (h1.get_tenant_ip(1), time)
        cmd += " > %s" % (os.path.join(dir, "memaslap.txt"))
        h2.cmd_async(cmd)
        h2.start_monitors(dir)

    def case3(self):
        self.case2(insert=True, out="case3")

    def case4(self):
        self.case1(out="case4")
        h1 = Host("10.0.1.17")
        h3 = Host("10.0.1.20")

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
                       '-t': self.opts("t"),
                       '-P': 16,
                       '-b': '3G',
                       '-u': True})
        self.procs.append(iperf.start_server(h1))
        self.procs.append(iperf.start_client(h3))

    def stop(self):
        for p in self.procs:
            p.kill()
        self.hlist.killall("memaslap")
        self.hlist.remove_tenants()

