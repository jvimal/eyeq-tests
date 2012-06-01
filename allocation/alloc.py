import argparse
from collections import namedtuple, defaultdict
import re

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

def print_formulation(flows, tx_flows, rx_flows):
    """
    @*x_flows is a dict mapping hosts, to tenants on that host,
    to flows at that host
    """

    def flow_var(flow):
        return "x%s%s%s%s" % (flow.src_host, flow.src_tenant, flow.dst_host, flow.dst_tenant)

    def p(cs):
        print " %s " % ",\n".join(cs)

    def add(vars):
        return " + ".join(vars)

    # Non-negativity
    constraints = []
    flowvars = []
    excessvars = []
    allvars = []
    for f in flows:
        var = flow_var(f)
        excessvar = var.replace("x", "e")
        constraints.append("%s >= 0" % var)
        constraints.append("%s >= 0" % excessvar)
        flowvars.append(var)
        excessvars.append(excessvar)
        allvars.append(var)
        allvars.append(excessvar)

    #print " { %s, " % (", ".join(constraints))
    endpoint_aggs = []

    # TX-Capacity,
    for host in sorted(tx_flows.keys()):
        vars = []
        for tid in sorted(tx_flows[host]):
            agg = []
            for flow in tx_flows[host][tid]:
                var = flow_var(flow)
                excessvar = var.replace("x", "e")
                vars.append("(%s + %s)" % (var, excessvar))
                agg.append(excessvar)
            endpoint_aggs.append(add(agg))
        constraints.append("%s <= 1" % add(vars))

    # RX capacity,
    for host in sorted(rx_flows.keys()):
        vars = []
        for tid in sorted(rx_flows[host]):
            agg = []
            for flow in rx_flows[host][tid]:
                var = flow_var(flow)
                excessvar = var.replace("x", "e")
                vars.append("(%s + %s)" % (var, excessvar))
                agg.append(excessvar)
            endpoint_aggs.append(add(agg))
        constraints.append("%s <= 1" % add(vars))

    def agg_var(dir, host, tid):
        return "%s%s%s" % (dir, host, tid)

    # Auxiliary TX variables
    for host in sorted(tx_flows.keys()):
        vars = []
        for tid in sorted(tx_flows[host]):
            var = agg_var("tx", host, tid)
            vars.append(var)
            allvars.append(var)
            constraints.append("%s >= 0" % var)
        constraints.append("%s <= 1" % add(vars))

    # Auxiliary RX variables
    for host in sorted(rx_flows.keys()):
        vars = []
        for tid in sorted(rx_flows[host]):
            var = agg_var("rx", host, tid)
            vars.append(var)
            allvars.append(var)
            constraints.append("%s >= 0" % var)
        constraints.append("%s <= 1" % add(vars))

    def prelude():
        print "U1[x_] := Log[x];"
        print "U2[x_] := -1/(3 x^(3));"
        print "U3[x_] := Log[x+1];"
        print ""
        print "Clear[%s];" % (",".join(allvars))
        print ""
        print "solve[f_] := FindMaximum["
        print "{ f, "

    def starting_points():
        st = []
        for var in allvars:
            start = "0.1"
            if var.startswith("e"):
                start = "0"
            st.append("{%s, %s}" % (var, start))
        print "}, { %s }" % ", ".join(set(st))
        print "]; "

    def solve():
        print ""
        print "sol = solve["
        addns = []
        caps = []
        for var in allvars:
            # Flowvars
            if var in flowvars:
                excessvar = var.replace("x", "e")
                addns.append("U1[%s + %s]" % (var, excessvar))
            elif var.startswith("tx") or var.startswith("rx"):
                caps.append("U2[%s]" % var)

        print add(addns + caps)

        print "+ 1000 * (",
        endpoint_aggs_utility = []
        for e in endpoint_aggs:
            endpoint_aggs_utility.append("U3[%s]" % e)
        print add(endpoint_aggs_utility),
        print ") "
        print "]; "

    def print_solution():
        print "Print[sol];"
        sums = []
        allocs = []
        for var in flowvars:
            evar = var.replace("x", "e")
            sums.append("%s + %s" % (var, evar))
            allocs.append("%s" % var.replace("x", "f"))
        print "{ %s } = ({ %s } /. sol[[2]]); " % (", ".join(allocs), (", ".join(sums)))

    prelude()
    p(constraints)
    starting_points()
    solve()
    print_solution()
    return

def main():
    flows = parse_input(args.file)
    hosts, tenants_list, tx_flows, rx_flows = stats(flows)

    print_formulation(flows, tx_flows, rx_flows)

main()
