#!/usr/bin/python
import sys
import argparse
import multiprocessing
from common import *
import termcolor as T
from expt import Expt
from iperf import Iperf
from time import sleep

sys.path = ['/root/vimal/10g/perfiso_10g_linux/tools'] + sys.path
import perfiso

parser = argparse.ArgumentParser(description="Perfiso RX overhead test.")
parser.add_argument('--rate',
                    dest="rate",
                    action="store",
                    help="Rate of VQ.",
                    required=True)

parser.add_argument('--dir',
                    dest="dir",
                    action="store",
                    help="Directory to store outputs.",
                    required=True)

parser.add_argument('-n',
                    dest="n",
                    action="store",
                    type=int,
                    help="Number of VQs.",
                    default=1)

parser.add_argument('-t',
                    dest="t",
                    action="store",
                    type=int,
                    help="Time to run expt in seconds.",
                    default=120)

parser.add_argument('--timeout',
                    dest="timeout",
                    action="store",
                    help="Timeout for VQ updates (in microseconds).",
                    default=str(100))

parser.add_argument('--without-vq',
                    dest="without_vq",
                    action="store_true",
                    help="Do expt without VQ",
                    default=False)

args = parser.parse_args()

if int(args.timeout) <= 10:
    print "Too low timeout, but nothing prevents you from setting it."
    sys.exit(0)

PI_PATH='python /root/vimal/10g/perfiso_10g_linux/tools/pi.py'

class RxOverhead(Expt):
    def prepare_iface(self, host, iface, ip):
        self.log("Preparing iface on %s" % host)
        cmds = ["ifconfig %s 0" % iface,
                "brctl addbr br0",
                "brctl addif br0 %s" % iface,
                "ifconfig br0 %s up" % (ip)]
        cmd_host(host, '; '.join(cmds))

    def start(self):
        dev="eth2"
        unload_module()
        remove_qdiscs()
        n = self.opts('n')
        load_module()

        self.prepare_iface("192.168.1.1", dev, "192.168.2.1")
        self.prepare_iface("192.168.1.2", dev, "192.168.2.2")

        self.log("Removing module")
        cmd_host("192.168.1.2", "rmmod perfiso; sleep 1")
        cmd_host("192.168.1.2",
                 "insmod /root/vimal/10g/perfiso_10g_linux/perfiso.ko iso_param_dev=%s" % dev)

        # VQ drain rate
        self.log("Loaded module")
        perfiso.params.set("ISO_VQ_DRAIN_RATE_MBPS", self.opts('rate'))

        # Create vq class
        self.log("Creating vq classes")
        for i in xrange(n):
            perfiso.txc.create(i + 1)
            perfiso.vqs.create(i + 1)
            perfiso.txc.associate(i+1, i+1)
        for i in xrange(n):
            cmd_host("192.168.1.2", "echo %d > %s/create_txc" % (i+1, perfiso.ISO_SYSFS))
            cmd_host("192.168.1.2", "echo %d > %s/create_vq" % (i+1, perfiso.ISO_SYSFS))
            cmd_host("192.168.1.2",
                     "echo associate txc %d vq %d > %s/assoc_txc_vq" % (i+1, i+1, perfiso.ISO_SYSFS))
        # Filter traffic to dest iperf port 5001+i to skb mark i+1
        cmd_host("192.168.1.2", "killall -9 iperf; iptables -F; ebtables -t broute -F")
        cmd("iptables -F; ebtables -t broute -F")
        self.log("Adding packet classifiers")

        for i in xrange(n):
            klass = i+1
            c = "ebtables -t broute -A BROUTING -p ip --ip-proto tcp "
            c += " --ip-dport %d --in-if %s" % (5000 + klass, dev)
            c += " -j mark --set-mark %d" % (klass)
            cmd(c)

            # TX
            c = "iptables -A OUTPUT --dst 192.168.2.2 -p tcp --sport %d " % (5000 + klass)
            c += " -j MARK --set-mark %d" % klass
            cmd(c)

        for i in xrange(n):
            klass = i+1
            c = "ebtables -t broute -A BROUTING -p ip --ip-proto tcp "
            c += " --ip-sport %d --in-if %s" % (5000 + klass, dev)
            c += " -j mark --set-mark %d" % (klass)
            cmd_host("192.168.1.2", c)

            # TX
            c = "iptables -A OUTPUT --dst 192.168.2.1 -p tcp --dport %d " % (5000 + klass)
            c += " -j MARK --set-mark %d" % klass
            cmd_host("192.168.1.2", c)

        self.log("Starting CPU/bandwidth monitors")
        # Start monitors
        m = multiprocessing.Process(target=monitor_cpu, args=("%s/cpu.txt" % self.opts('dir'),))
        self.start_monitor(m)
        m = multiprocessing.Process(target=monitor_bw, args=("%s/net.txt" % self.opts('dir'),))
        self.start_monitor(m)
        m = multiprocessing.Process(target=monitor_perf,
                                    args=("%s/perf.txt" % self.opts('dir'), self.opts('t')))
        self.start_monitor(m)

        self.log("Starting %d iperfs" % n)

        # Start iperfs servers
        for i in xrange(n):
            klass = i+1
            port = 5000 + klass
            parallel = 4
            iperf = Iperf({'-p': port,
                           '-P': parallel,
                           '-c': '192.168.2.2'})
            server = iperf.start_server('192.168.2.1')
            self.procs.append(server)
            self.log("server %d" % klass)

        sleep(1)
        for i in xrange(n):
            klass = i+1
            port = 5000 + klass
            iperf = Iperf({'-p': port,
                           '-P': parallel,
                           '-c': '192.168.2.1',
                           '-t': self.opts('t')})
            client = iperf.start_client('192.168.2.2')
            self.procs.append(client)
            self.log("client %d" % klass)
            sleep(0.1)

    def stop(self):
        for p in self.procs:
            p.kill()
        killall()

class RxOverhead2(Expt):
    def prepare_iface(self, host, iface, ip):
        self.log("Preparing iface on %s" % host)
        cmds = ["ifconfig %s 0" % iface,
                "brctl addbr br0",
                "brctl addif br0 %s" % iface,
                "ifconfig br0 %s up" % (ip)]
        cmd_host(host, '; '.join(cmds))

    def start(self):
        dev="eth2"
        unload_module()
        remove_qdiscs()
        n = self.opts('n')

        self.prepare_iface("192.168.1.1", dev, "192.168.2.1")
        self.prepare_iface("192.168.1.2", dev, "192.168.2.2")

        self.log("Removing module")
        cmd_host("192.168.1.2", "rmmod perfiso; sleep 1")
        cmd_host("192.168.1.2",
                 "insmod /root/vimal/10g/perfiso_10g_linux/perfiso.ko iso_param_dev=%s" % dev)

        # Restrict aggregate drain rate
        cmd_host("192.168.1.2",
                 "echo %s > /proc/sys/perfiso/ISO_MAX_TX_RATE" % self.opts('rate'))

        # Create vq class
        for i in xrange(1):
            cmd_host("192.168.1.2", "echo %d > %s/create_txc" % (i+1, perfiso.ISO_SYSFS))
            cmd_host("192.168.1.2", "echo %d > %s/create_vq" % (i+1, perfiso.ISO_SYSFS))
            cmd_host("192.168.1.2",
                     "echo associate txc %d vq %d > %s/assoc_txc_vq" % (i+1, i+1, perfiso.ISO_SYSFS))
        # Filter traffic to dest iperf port 5001+i to skb mark i+1
        cmd_host("192.168.1.2", "killall -9 iperf; iptables -F; ebtables -t broute -F")
        cmd("iptables -F; ebtables -t broute -F")
        self.log("Adding packet classifiers")

        for i in xrange(1):
            klass = i+1
            c = "ebtables -t broute -A BROUTING -p ip --ip-proto tcp "
            c += " --in-if %s" % (dev)
            c += " -j mark --set-mark %d" % (klass)
            cmd(c)

            # TX
            c = "iptables -A OUTPUT --dst 192.168.2.2 -p tcp "
            c += " -j MARK --set-mark %d" % klass
            cmd(c)

        for i in xrange(n):
            klass = i+1
            c = "ebtables -t broute -A BROUTING -p ip --ip-proto tcp "
            c += " --in-if %s" % (dev)
            c += " -j mark --set-mark %d" % (klass)
            cmd_host("192.168.1.2", c)

            # TX
            c = "iptables -A OUTPUT --dst 192.168.2.1 -p tcp "
            c += " -j MARK --set-mark %d" % klass
            cmd_host("192.168.1.2", c)

        self.log("Starting CPU/bandwidth monitors")
        # Start monitors
        m = multiprocessing.Process(target=monitor_cpu, args=("%s/cpu.txt" % self.opts('dir'),))
        self.start_monitor(m)
        m = multiprocessing.Process(target=monitor_bw, args=("%s/net.txt" % self.opts('dir'),))
        self.start_monitor(m)
        m = multiprocessing.Process(target=monitor_perf,
                                    args=("%s/perf.txt" % self.opts('dir'), self.opts('t')))
        self.start_monitor(m)

        self.log("Starting %d iperfs" % n)

        # Start iperfs servers
        for i in xrange(n):
            klass = i+1
            port = 5000 + klass
            parallel = 4
            iperf = Iperf({'-p': port,
                           '-P': parallel,
                           '-c': '192.168.2.2'})
            server = iperf.start_server('192.168.2.1')
            self.procs.append(server)
            self.log("server %d" % klass)

        sleep(1)
        for i in xrange(n):
            klass = i+1
            port = 5000 + klass
            iperf = Iperf({'-p': port,
                           '-P': parallel,
                           '-c': '192.168.2.1',
                           '-t': self.opts('t')})
            client = iperf.start_client('192.168.2.2')
            self.procs.append(client)
            self.log("client %d" % klass)
            sleep(0.1)

    def stop(self):
        for p in self.procs:
            p.kill()
        killall()

if not args.without_vq:
    RxOverhead({
            'n': args.n,
            'dir': args.dir,
            'rate': args.rate,
            't': args.t,
            'timeout': args.timeout,
            }).run()
else:
    RxOverhead2({
            'n': args.n,
            'dir': args.dir,
            'rate': args.rate,
            't': args.t,
            'timeout': args.timeout,
            }).run()
