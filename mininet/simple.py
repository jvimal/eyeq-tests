#!/usr/bin/python

from mininet.topo import Topo
from mininet import node
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import lg
from mininet.link import TCLink

from subprocess import Popen, PIPE
from time import sleep, time
import multiprocessing
import termcolor as T
import argparse
import random
import sys
import os

parser = argparse.ArgumentParser(description="EyeQ test topology in Mininet")
args = parser.parse_args()

lg.setLogLevel('info')

def cmd(h, c):
    print c
    h.sendCmd(c)
    h.waitOutput()

def rootcmd(c):
    print c
    Popen(c, shell=True).wait()

class StarTopo(Topo):
    def __init__(self, n=3):
        super(StarTopo, self).__init__()
        hosts = []
        for i in xrange(n):
            name = 'h%d' % (i + 1)
            host = self.addHost(name)
            hosts.append(host)
        switch = self.addSwitch('s0')
        for h in hosts:
            self.addLink(h, switch)
        return

def ssh_init(net):
    for host in net.hosts:
        cmd(host, "/usr/sbin/sshd")
    return

def eyeq_conf():
    return

def main():
    topo = StarTopo(n=4)
    net = Mininet(topo=topo)
    net.start()
    ssh_init(net)
    CLI(net)
    net.stop()
    return

main()

