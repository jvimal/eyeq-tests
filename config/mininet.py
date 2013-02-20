
"""
This is a sample configuration when running EyeQ on Mininet.
"""

PI_MODULE = '/home/ubuntu/eyeq/perfiso.ko'
IP_PREFIX = '10.0.0'
IP_FMT = IP_PREFIX + ".%d"

host_ips = map(lambda i: IP_FMT % i, range(1, 21))

def pick_host_ip(i):
    return host_ips[i]

def pick_10g_ip(i):
    return host_ips[i].replace(IP_PREFIX, "192.168.2")

def pick_1g_ip(i):
    return host_ips[i].replace(IP_PREFIX, "192.168.1")

def pick_host_name(i):
    return host_ips[i].replace(IP_PREFIX, "h")

PI_DEV = {}
host_id = 1
for host in host_ips:
    PI_DEV[host_id] = 'h%d-eth0' % host_id
    host_id += 1
