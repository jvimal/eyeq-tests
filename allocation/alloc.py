import argparse
from collections import namedtuple, defaultdict
import re

# Library of formulations
import f1
import f2
import f3

parser = argparse.ArgumentParser(description="Allocation algorithm.")

parser.add_argument('--file',
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
    tx_flows = defaultdict(lambda: defaultdict(list))
    rx_flows = defaultdict(lambda: defaultdict(list))
    for f in flows:
        hosts.add(f.src_host)
        hosts.add(f.dst_host)
        tenants[f.src_host].add(f.src_tenant)
        tenants[f.dst_host].add(f.dst_tenant)

        tx_flows[f.src_host][f.src_tenant].append(f)
        rx_flows[f.dst_host][f.dst_tenant].append(f)
    for k in tenants.keys():
        v = list(sorted(tenants[k]))
        tenants_list[k] = v
    hosts = list(sorted(hosts))
    return hosts, tenants_list, tx_flows, rx_flows

def main():
    flows = parse_input(args.file)
    hosts, tenants_list, tx_flows, rx_flows = stats(flows)

    #f1.print_formulation(flows, tx_flows, rx_flows)
    f2.print_formulation(flows, tx_flows, rx_flows)
    #f3.print_formulation(flows, tx_flows, rx_flows)
main()
