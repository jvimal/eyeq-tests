
"""
This is the most recent configuration of the lancelots in the Packard
cluster.  This will change if we are running on Mininet.
"""

PI_MODULE = '/root/vimal/10g/perfiso_10g_linux/perfiso.ko'
PI_MODULE = '/root/vimal/10g/modules/perfiso.ko'
PI_MODULE = '/root/vimal/exports/perfiso.ko'

host_ips = map(lambda i: "10.0.1.%d" % i, range(1, 21))
host_ips_exclude = ["10.0.1.9", "10.0.1.11", "10.0.1.12", "10.0.1.18"]
for ip in host_ips_exclude:
    host_ips.remove(ip)

def pick_host_ip(i):
    return host_ips[i]

def pick_10g_ip(i):
    return host_ips[i].replace("10.0.1", "192.168.2")

def pick_1g_ip(i):
    return host_ips[i].replace("10.0.1", "192.168.1")

def pick_host_name(i):
    return host_ips[i].replace("10.0.1.", "l")

eth1 = 'eth1'

PI_DEV = {
    3: 'eth3',
    6: 'eth4',
    7: 'eth3',
    10: 'eth6',
    16: eth1,
    17: eth1,

    19: eth1,
    20: eth1,
    }

PI_1G_DEV = {
    1: eth1,
    2: eth1,
    4: eth1,
    }
