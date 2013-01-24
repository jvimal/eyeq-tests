#!/bin/bash

python ~/iso/tests/plots/plot_tenant_rate.py -f udp-mtu9000-s100G-with--enabled/l1/tenant.txt --rx --title "" --accum 2 -o plot-zoom.pdf --range 33.1:33.20 -l TCP UDP --nototal --rect

