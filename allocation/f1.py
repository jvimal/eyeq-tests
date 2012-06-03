# Some formulation

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

    def agg_var(dir, host, tid):
        return "%s%s%s" % (dir, host, tid)

    minmax_constraints = []

    # TX-Capacity,
    for host in sorted(tx_flows.keys()):
        vars = []
        for tid in sorted(tx_flows[host]):
            agg = []
            aggflows = []
            for flow in tx_flows[host][tid]:
                var = flow_var(flow)
                excessvar = var.replace("x", "e")
                vars.append("(%s + %s)" % (var, excessvar))
                agg.append(excessvar)
                aggflows.append(var)
            endpoint_aggs.append(add(agg))

            aggvar = agg_var("tx", host, tid)
            minmax_constraints.append("%s <= %s" % (add(aggflows), aggvar))
        constraints.append("%s <= 1" % add(vars))

    # RX capacity,
    for host in sorted(rx_flows.keys()):
        vars = []
        for tid in sorted(rx_flows[host]):
            agg = []
            aggflows = []
            for flow in rx_flows[host][tid]:
                var = flow_var(flow)
                excessvar = var.replace("x", "e")
                vars.append("(%s + %s)" % (var, excessvar))
                agg.append(excessvar)
                aggflows.append(var)
            endpoint_aggs.append(add(agg))

            aggvar = agg_var("rx", host, tid)
            minmax_constraints.append("%s <= %s" % (add(aggflows), aggvar))

        constraints.append("%s <= 1" % add(vars))

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
        print "U1[x_] := -1/x;"
        print "U2[x_] := -1/(5 x^(5));"
        print "U3[x_] := 1000 Log[x+1];"
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
                #addns.append("U1[%s + %s]" % (var, excessvar))
                addns.append("U1[%s]" % var)
            elif var.startswith("tx") or var.startswith("rx"):
                caps.append("U2[%s]" % var)

        print " 10000 * (%s) " % add(addns + caps)

        print "+ (",
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
        print "{ %s } = ({ %s } /. sol[[2]]) " % (", ".join(allocs), (", ".join(sums)))

    prelude()
    p(constraints + minmax_constraints)
    starting_points()
    solve()
    print_solution()
    return
