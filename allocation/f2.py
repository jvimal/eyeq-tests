# Some formulation
from collections import defaultdict
import random

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
        hostagg = []
        for tid in sorted(tx_flows[host]):
            agg = []
            for flow in tx_flows[host][tid]:
                var = flow_var(flow)
                agg.append(var)
                hostagg.append(var)
            cap = agg_var("tx", host, tid)
            capvars.append(cap)
            constraints.append("%s <= (1+gc) %s" % (add(agg), cap))
            aggvars.append(add(agg))
        constraints.append("%s <= 1" % add(hostagg))

    # RX
    for host in sorted(rx_flows.keys()):
        hostagg = []
        for tid in sorted(rx_flows[host]):
            agg = []
            for flow in rx_flows[host][tid]:
                var = flow_var(flow)
                agg.append(var)
                hostagg.append(var)
            cap = agg_var("rx", host, tid)
            capvars.append(cap)
            constraints.append("%s <= (1+gc) %s" % (add(agg), cap))
            aggvars.append(add(agg))
        constraints.append("%s <= 1" % add(hostagg))

    def start():
        print "optflow[capsol_] := Module[{}, "
        tmp = ",".join(capvars)

        # Clear all caps
        print "Clear[%s];" % tmp
        print "Clear[f];"
        # Clear all flowvars
        print "Clear[%s];" % ",".join(flowvars)

        print "{%s} = If[Length[capsol] > 0," % tmp
        print "    ({%s} /. capsol), " % (tmp)
        tmp2 = ",".join(["%.2f" % (random.random()) for var in capvars])
        #tmp2 = ",".join(["Random[]"  for var in capvars])
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

        print "Return[Sort@flowsol];"
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
                agg.append(add([var, "df"]))
            cap = agg_var("tx", host, tid)
            capvars.append(cap)
            constraints.append("0 <= %s <= (1+gf) (%s)" % (cap, add(agg)))
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
                agg.append(add([var, "df"]))
            cap = agg_var("rx", host, tid)
            capvars.append(cap)
            constraints.append("0 <= %s <= (1+gf) (%s)" % (cap, add(agg)))
            aggvars.append(add(agg))
            hostagg.append(cap)
        constraints.append("%s <= 1" % add(hostagg))

    def start():
        print "optcap[flowsol_] := Module[{}, "
        tmp = ",".join(flowvars)

        # Clear all caps
        print "Clear[%s];" % ",".join(capvars)
        print "Clear[f];"
        # Clear all flowvars
        print "Clear[%s];" % tmp

        # Assign all flows
        rands = ",".join(["%.2f" % random.random() for var in flowvars])
        #rands = ",".join(["Random[]" for var in flowvars])
        print "{%s} = If[Length[flowsol] > 0,\n ({%s} /. flowsol),\n {%s}];" % (tmp, tmp, rands)

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

        print "Return[Sort@capsol];"
        print "]; "

    start()
    solve()
    starting_points()
    end()
    return

def iterate():
    print "run := Reap[ Module[{},"
    print "flowsol1 = optflow[{}];"
    print "capsol1 = {{}, {}};"

    print "flowsol2 = {{}, {}};"
    print "capsol2 = optcap[{}];"

    print "For[i=0,"
    print "i < niter,"
    print "i++,"
    print "  capsol1 = optcap[ flowsol1[[2]] ];"
    print "  flowsol2 = optflow[ capsol2[[2]] ];"
    #print "  Print[\"**********\"];"
    #print "  Print[\"capsol\", i, \":\", Sort@capsol];"

    print "  Sow[capsol1,  \"cs1\"];"
    print "  Sow[flowsol1, \"fs1\"];"

    print "  Sow[capsol2,  \"cs2\"];"
    print "  Sow[flowsol2, \"fs2\"];"

    print "  capsol2 = optcap[ flowsol2[[2]] ];"
    print "  flowsol1 = optflow[ capsol1[[2]] ];"
    print '   Print["iteration: ", i];'
    #print "  Print[\"flowsol\", i, \":\", Sort@flowsol];"
    print "];"

    print "NormaliseSol[sol_, scale_] := Sort@(sol /. (Rule[x_,y_] :> Rule[x,y/scale]));"
    print "Print[NormaliseSol[flowsol, 1]];"
    print "Print[NormaliseSol[capsol, 1]];"
    print "], "
    print '{"cs1", "fs1", "cs2", "fs2"}'
    print '];'
    return

def utilities():
    print "Clear[U1, U2, U3];"
    print "U[a_,x_] := If[a==1, Log[x], -1/((a-1) x^(a-1))];"
    print "U1[x_] := U[1,x];"
    print "U2[x_] := U[7,x];"
    print "U3[x_] := 1000 Log[x+1];"
    print "U4[x_,a_] := 1/(1+Exp[ 10 (x - a) ]);"

def plot():
    print "sol = run;"
    print "data = First /@ Flatten[#,1]& /@ sol[[2]];"
    print "scale[x_] := x/Max[x];"
    print 'cs1 = data[[1]];'
    print 'fs1 = data[[2]];'
    print 'ListLogPlot[{scale@cs1, scale@fs1}, Joined->True]'
    #print 'data = { Normalise /@ Flatten /@ series1[[2]], '
    #print '  Normalise /@ Flatten /@ series2[[2]] };'
    #print 'ListLogPlot[#, Joined -> True]& /@ data'
    return

def print_formulation(flows, tx_flows, rx_flows):
    """
    @*x_flows is a dict mapping hosts, to tenants on that host,
    to flows at that host
    """
    utilities()
    print "gc=0; gf=0.1; niter=50; df=0.0;"
    optflow(flows, tx_flows, rx_flows)
    print ""
    print ""
    optcap(flows, tx_flows, rx_flows)
    print ""
    print ""
    iterate()
    print ""
    plot()
    return
