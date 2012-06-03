# Some formulation
from collections import defaultdict

"""
Sandwhich formulation...  iterative optimisation problems:

Initial solution {cj}: Equalise capacities.

OPT1: given (inflated) capacities, solve for flow values.
OPT2: given demands (sum of flow values at an endpoint in OPT1), solve for capacities.
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

def optflow(flows, tx_flows, rx_flows):
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
        for tid in sorted(tx_flows[host]):
            agg = []
            for flow in tx_flows[host][tid]:
                var = flow_var(flow)
                agg.append(var)
            cap = agg_var("tx", host, tid)
            capvars.append(cap)
            constraints.append("%s <= (1+g) %s" % (add(agg), cap))
            aggvars.append(add(agg))

    # RX
    for host in sorted(rx_flows.keys()):
        for tid in sorted(rx_flows[host]):
            agg = []
            for flow in rx_flows[host][tid]:
                var = flow_var(flow)
                agg.append(var)
            cap = agg_var("rx", host, tid)
            capvars.append(cap)
            constraints.append("%s <= (1+g) %s" % (add(agg), cap))
            aggvars.append(add(agg))

    def start():
        print "optflow[capsol_] := Module[{g=0.1}, "
        tmp = ",".join(capvars)

        # Clear all caps
        print "Clear[%s];" % tmp
        print "Clear[f];"
        # Clear all flowvars
        print "Clear[%s];" % ",".join(flowvars)

        print "{%s} = If[Length[capsol] > 0," % tmp
        print "    ({%s} /. capsol), " % (tmp)
        tmp2 = ",".join(["0.5" for var in capvars])
        print "    {%s}" % (tmp2)
        print "];"

        utilities = [ ("U1[%s]" % f) for f in flowvars ]
        print "f=%s;" % add(utilities)

    def solve():
        print "flowsol = FindMaximum[{f,"
        p(constraints)

    def starting_points():
        st = []
        for var in flowvars:
            start = "0.1"
            st.append("{%s, %s}" % (var, start))
        print "}, { %s }" % ", ".join(set(st))
        print "]; " #(* end FindMaximum *)"

    def end():
        # Clear all caps
        print "Clear[%s];" % ",".join(capvars)
        print "Clear[f];"
        # Clear all flowvars
        print "Clear[%s];" % ",".join(flowvars)

        print "Return[flowsol[[2]]];"
        print "]; "

    start()
    solve()
    starting_points()
    end()
    return

def optcap(flows, tx_flows, rx_flows):
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
        hostagg = []
        for tid in sorted(tx_flows[host]):
            agg = []
            for flow in tx_flows[host][tid]:
                var = flow_var(flow)
                agg.append(var)
            cap = agg_var("tx", host, tid)
            capvars.append(cap)
            constraints.append("0 <= %s <= %s" % (cap, add(agg)))
            aggvars.append(add(agg))
            hostagg.append(cap)
        constraints.append("%s <= 1" % add(hostagg))

    # RX
    for host in sorted(rx_flows.keys()):
        hostagg = []
        for tid in sorted(rx_flows[host]):
            agg = []
            for flow in rx_flows[host][tid]:
                var = flow_var(flow)
                agg.append(var)
            cap = agg_var("rx", host, tid)
            capvars.append(cap)
            constraints.append("0 <= %s <= %s" % (cap, add(agg)))
            aggvars.append(add(agg))
            hostagg.append(cap)
        constraints.append("%s <= 1" % add(hostagg))

    def start():
        print "optcap[flowsol_] := Module[{g=0.1}, "
        tmp = ",".join(flowvars)

        # Clear all caps
        print "Clear[%s];" % ",".join(capvars)
        print "Clear[f];"
        # Clear all flowvars
        print "Clear[%s];" % tmp

        # Assign all flows
        print "{%s} = ({%s} /. flowsol);" % (tmp, tmp)

        utilities = [ ("U2[%s]" % c) for c in capvars ]
        print "f=%s;" % add(utilities)

    def solve():
        print "capsol = FindMaximum[{f,"
        p(constraints)

    def starting_points():
        st = []
        for var in capvars:
            start = "0.1"
            st.append("{%s, %s}" % (var, start))
        print "}, { %s }" % ", ".join(set(st))
        print "]; " #(* end FindMaximum *)"

    def end():
        # Clear all caps
        print "Clear[%s];" % ",".join(capvars)
        print "Clear[f];"
        # Clear all flowvars
        print "Clear[%s];" % ",".join(flowvars)

        print "Return[capsol[[2]]];"
        print "]; "

    start()
    solve()
    starting_points()
    end()
    return

def iterate():
    print "flowsol = optflow[{}];"
    print "capsol = {};"
    print "For[i=0,"
    print "i < 5,"
    print "i++,"
    print "  capsol = optcap[flowsol];"
    print "  Print[\"**********\"];"
    print "  Print[\"capsol\", i, \":\", Sort@capsol];"
    print "  flowsol = optflow[capsol];"
    print "  Print[\"flowsol\", i, \":\", Sort@flowsol];"
    print "];"

    print "Print[Sort@flowsol];"
    print "Print[Sort@capsol];"
    return


def utilities():
    print "Clear[U1, U2, U3];"
    print "U[a_,x_] := If[a==1, Log[x], -1/((a-1) x^(a-1))];"
    print "U1[x_] := U[1,x];"
    print "U2[x_] := U[10,x];"
    print "U3[x_] := 1000 Log[x+1];"

def print_formulation(flows, tx_flows, rx_flows):
    """
    @*x_flows is a dict mapping hosts, to tenants on that host,
    to flows at that host
    """
    utilities()
    optflow(flows, tx_flows, rx_flows)
    print ""
    print ""
    optcap(flows, tx_flows, rx_flows)
    print ""
    print ""
    iterate()
    return
