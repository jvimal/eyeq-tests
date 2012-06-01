from expt import Expt
from host import *
from iperf import Iperf
from time import sleep
import argparse
import re
from collections import defaultdict, namedtuple

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
                        help="Topology input file",
                        required=True)

    args = parser.parse_args()


"""
Example traffic matrix input file:

# comment line
src-host-id   src-tenant-id    dst-host-id   dst-tenant-id
"""

Flow = namedtuple('Flow', ['src_host', 'src_tenant', 'dst_host', 'dst_tenant'])
def parse_input(filename):
    pat_space = re.compile(r'\s+')
    ret = []
    f = open(filename)
    for line in f.xreadlines():
        if line.startswith('#'):
            continue
        line = line.strip()
        if len(line) == 0:
            continue
        try:
            a, b, c, d = pat_space.split(line)
            ret.append(Flow(src_host=a, src_tenant=b,
                            dst_host=c, dst_tenant=d))
        except:
            print "Error parsing line", line, "ignoring..."
    f.close()
    return ret

def stats(flows):
    """Returns:
    num_hosts: number of hosts in the set of flows.
    num_tenants[H]: number of tenants in host H
    """
    hosts = set([])
    tenants = defaultdict(set)
    tenants_list = {}
    for f in flows:
        hosts.add(f.src_host)
        hosts.add(f.dst_host)
        tenants[f.src_host].add(f.src_tenant)
        tenants[f.dst_host].add(f.dst_tenant)
    for k in tenants.keys():
        v = list(sorted(tenants[k]))
        tenants_list[k] = v
    hosts = list(sorted(hosts))
    return hosts, tenants_list

class Allocation(Expt):
    def start(self):
        # Parse the topology input file
        flows = parse_input(self.opts('topo'))

        # Find the number of tenants in the flows
        hosts, tenants = stats(flows)

        hlist = HostList()
        name_to_host = {}
        name_to_tenant = defaultdict(defaultdict)
        for i, name in enumerate(hosts):
            h = Host(pick_host_ip(i))
            h.__host_name = name
            name_to_host[name] = h
            hlist.append(h)
        hlist.prepare_iface()
        hlist.rmmod()
        hlist.insmod()
        self.hlist = hlist

        # Create the tenants on each host
        for h in hlist.lst:
            T = tenants[h.__host_name]
            for tid, tname in enumerate(T):
                print "tid: %s, tname: %s" % (tid, tname)
                h.create_ip_tenant(tid+1)
                name_to_tenant[h.__host_name][tname] = tid

        hlist.perfiso_set("ISO_VQ_DRAIN_RATE_MBPS", self.opts("vqrate"))
        hlist.perfiso_set("ISO_MAX_TX_RATE", self.opts("vqrate"))
        hlist.start_monitors(self.opts("dir"), 1e5)

        def start_flow(srch, src_tid, dsth, dst_tid):
            client = Iperf({'-c': dsth.get_tenant_ip(dst_tid+1),
                            '-t': self.opts('t'),
                            '-B': srch.get_tenant_ip(src_tid+1),
                            'dir': self.opts('dir'),
                            '-P': 2})
            client.start_client(srch)

        # find all sinks
        servers_done = []
        for flow in flows:
            sname = flow.dst_host
            if sname not in servers_done:
                h = name_to_host[sname]
                h.cmd_async("iperf -s")
                servers_done.append(sname)

        # start all the flows
        for flow in flows:
            src_host = name_to_host[flow.src_host]
            dst_host = name_to_host[flow.dst_host]

            src_tid = name_to_tenant[flow.src_host][flow.src_tenant]
            dst_tid = name_to_tenant[flow.dst_host][flow.dst_tenant]
            start_flow(src_host, src_tid,
                       dst_host, dst_tid)
        return

    def stop(self):
        self.hlist.remove_tenants()
        self.hlist.copy("l1", self.opts("dir"), self.opts("exptid"))
        self.hlist.killall("iperf")

if __name__ == "__main__":
    Allocation(vars(args)).run()
