
import ipaddr
import sys
import os
sys.path.append('/root/iso/tests')
from host import Host

tor0 = [1, 2, 3, 4, 5]
tor1 = [6, 7, 8, 10, 13]

net0 = ipaddr.ip_network('192.168.1.16/28')
net1 = ipaddr.ip_network('192.168.1.32/28')

DEV = {
    1: 'eth1',
    2: 'eth1',
    3: 'eth1',
    4: 'eth1',
    5: 'eth1',

    6: 'eth1',
    7: 'eth1',
    8: 'eth1',
    10: 'eth1',
    13: 'eth1'
    }

def ip(num):
    return '10.0.1.%d' % num

#hosts = [Host(ip(i)) for i in tor0 + tor1]

def configure(tor, net):
    for num,ipaddr in zip(tor, net):
        print ip(num), ipaddr
        host = Host(ip(num))
        host.cmd("ifconfig %s %s" % (DEV.get(num), ipaddr))


configure(tor0, net0)
print '--'
configure(tor1, net1)

