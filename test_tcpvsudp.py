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
            try:
                ip = pick_host_ip(i)
                hi = Host(ip)
                hlist.append(hi)
                hlist_udp.append(hi)
            except:
                pass

        self.hlist = hlist
        hlist.prepare_iface()

        hlist.rmmod()
        hlist.insmod()
        self.log("Creating two tenants")
        h1.create_ip_tenant(tid=1)
        h1.create_ip_tenant(tid=2)
        # Set the weight for TCP tenant.  UDP's weight is 1
        h1.perfiso_set_vq_weight(vq=h1.get_tenant_ip(1),
                                 weight=self.opts("wtcp"))

        if self.opts("mtu"):
            hlist.set_mtu(self.opts("mtu"))
        else:
            hlist.set_mtu("1500")
        h2.create_ip_tenant(tid=1)
        hlist_udp.create_ip_tenant(2)
        sleep(1)
        hlist.setup_tenant_routes()
        if self.opts("enabled"):
            hlist.perfiso_set("IsoAutoGenerateFeedback", "1")
            hlist.perfiso_set("ISO_VQ_DRAIN_RATE_MBPS", self.opts("vqrate"))
            hlist.perfiso_set("ISO_VQ_UPDATE_INTERVAL_US", self.opts("vqupdate"))
            hlist.perfiso_set("ISO_RFAIR_INITIAL", 9000)
            # don't muck around with parameters
            #if self.opts("aimd_dt_us"):
                #hlist.perfiso_set("ISO_RFAIR_DECREASE_INTERVAL_US", self.opts("aimd_dt_us"))
                #hlist.perfiso_set("ISO_RFAIR_INCREASE_INTERVAL_US", self.opts("aimd_dt_us"))
                # At 500us, we increment by 1Mbps.  So let's use this
                # to scale our increment accordingly
                #increment = max(1, self.opts("ai") * int(self.opts("aimd_dt_us")) / 500)
                #hlist.perfiso_set("ISO_RFAIR_INCREMENT", "%s" % increment)
                #hlist.perfiso_set("ISO_FALPHA", "%s" % self.opts("md"))
        else:
            hlist.perfiso_set("IsoAutoGenerateFeedback", 0)
            hlist.perfiso_set("ISO_VQ_DRAIN_RATE_MBPS", 100000)
            hlist.perfiso_set("ISO_VQ_UPDATE_INTERVAL_US", 1000000)
            hlist.perfiso_set("ISO_RFAIR_INITIAL", 100000)
            hlist.perfiso_set("ISO_MAX_TX_RATE", 100000)
        hlist.start_monitors(self.opts("dir"), 1e3)

        self.procs = []
        if self.opts("tcptest") == "xput":
            # Start iperf servers
            iperf = Iperf({'-p': 5001})
            server = iperf.start_server(h1)
            self.procs.append(server)

            sleep(1)
            # Start P TCP connection from h2 to h1
            opts = {'-p': 5001,
                    '-c': h1.get_10g_ip(),
                    '-t': self.opts("t"),
                    'dir': self.opts("dir"),
                    '-P': self.opts("P")}

            opts['-c'] = h1.get_tenant_ip(1)
            client = Iperf(opts)
            client = client.start_client(h2)
            self.procs.append(client)
        elif self.opts("tcptest") == "latency":
            # Start netperf server
            hlist.cmd("rmmod r2d2")
            h1.start_netperf_server()
            sleep(1)
            out = os.path.join(self.opts("dir"), "netperf_rr.txt")
            opts = "-v 2 -H %s -l %s " % (h1.get_tenant_ip(1), self.opts("t"))
            opts += " -t TCP_RR -D 1,s -- -r %s -D " % self.opts("rrsize")
            h2.start_netperf_client(opts=opts, out=out)

        if self.opts("traffic"):
            for hi in hlist.lst:
                LOADGEN = "taskset -c 7 /root/vimal/exports/loadgen"
                ip = hi.get_tenant_ip(2)
                out = os.path.join(self.opts("dir"), "loadgen.txt")
                cmd = "%s -i %s " % (LOADGEN, ip)
                cmd += "-l 12345 -p 500000 -f %s > %s" % (self.opts("traffic"), out)
                hi.cmd_async(cmd)
            # Start it
            sleep(5)
            execs = []
            for hi in hlist.lst:
                ip = hi.get_tenant_ip(2)
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
                opts['-c'] = h1.get_tenant_ip(2)
                client = Iperf(opts)
                client = client.start_client(hi)
                self.procs.append(client)

    def stop(self):
        self.hlist.set_mtu("1500")
        self.hlist.killall("loadgen")
        self.hlist.remove_tenants()
        self.hlist.copy("l1", self.opts("dir"), self.opts("exptid"))
        for p in self.procs:
            p.kill()
