# Some formulation
from collections import defaultdict
import random

"""
Simple, independent per-flow, per-endpoint formulation, that can be
used as a template for other formulations...
"""

def flow_var(flow):
    return "x%s%s%s%s" % (flow.src_host, flow.src_tenant, flow.dst_host, flow.dst_tenant)

def agg_var(dir, host, tid):
    return "%s%s%s" % (dir, host, tid)

def positive(var):
    return "%s >= 0" % var

def p(cs):
    print "%s" % ",\n".join(cs)

def add(vars):
    return " + ".join(vars)

def formulate(flows, tx_flows, rx_flows):
    constraints = []
    flowvars = []
    allvars = []
    capvars = []
    aggvars = []

    for f in flows:
        var = flow_var(f)
        constraints.append(positive(var))
        flowvars.append(var)
        allvars.append(var)

    # TX
    for host in sorted(tx_flows.keys()):
        hostflowagg = []
        hostcapagg = []
        for tid in sorted(tx_flows[host]):
            tenantflowagg = []
            for flow in tx_flows[host][tid]:
                var = flow_var(flow)
                tenantflowagg.append(var)
                hostflowagg.append(var)
            cap = agg_var("tx", host, tid)
            constraints.append("0 <= %s <= 1" % cap)
            constraints.append("%s <= %s" % (add(tenantflowagg), cap))
            capvars.append(cap)
            hostcapagg.append(cap)
        allvars += capvars
        constraints.append("%s <= 1" % add(hostflowagg))
        constraints.append("%s <= 1" % add(hostcapagg))

    # RX
    for host in sorted(rx_flows.keys()):
        hostflowagg = []
        hostcapagg = []
        for tid in sorted(rx_flows[host]):
            tenantflowagg = []
            for flow in rx_flows[host][tid]:
                var = flow_var(flow)
                tenantflowagg.append(var)
                hostflowagg.append(var)
            cap = agg_var("rx", host, tid)
            constraints.append("0 <= %s <= 1" % cap)
            constraints.append("%s <= %s" % (add(tenantflowagg), cap))
            capvars.append(cap)
            hostcapagg.append(cap)
        allvars += capvars
        constraints.append("%s <= 1" % add(hostflowagg))
        constraints.append("%s <= 1" % add(hostcapagg))


    def start():
        print 'solve[f_] := FindMaximum[{f,'

    def starting_points():
        st = []
        for var in allvars:
            start = "0.1"
            st.append("{%s, %s}" % (var, start))
        print "}, { %s }" % ", ".join(set(st))
        print "]; "

    def solve():
        print ''
        print 'sol = solve['
        flow_utilities = []
        cap_utilities = []
        for var in flowvars:
            flow_utilities.append("U1[%s]" % var)
        for var in capvars:
            cap_utilities.append("U2[%s]" % var)
        print add(flow_utilities)
        print "+", add(cap_utilities)
        print ']'

    start()
    p(constraints)
    starting_points()
    solve()
    return

def utilities():
    print "Clear[U, U1, U2, U3];"
    print "U[a_,x_] := If[a==1, Log[x], -1/((a-1) x^(a-1))];"
    print "U1[x_] := U[1,x];"
    print "U2[x_] := U[7,x];"
    print "U3[x_] := 1000 Log[x+1];"


def print_formulation(flows, tx_flows, rx_flows):
    """
    @*x_flows is a dict mapping hosts, to tenants on that host,
    to flows at that host
    """
    utilities()
    formulate(flows, tx_flows, rx_flows)
    return
