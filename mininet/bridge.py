
from mininet.node import Switch
from mininet.util import quietRun

class LinuxBridge(Switch):
    """The Linux Bridge for Mininet.  Much simpler than the
    OVSKernelSwitch and all its complex machinary."""
    def __init__(self, name, **kwargs):
        Switch.__init__(self, name, **kwargs)

    @staticmethod
    def setup():
        pass # for now

    def start(self, controllers):
        # Controller support isnt there for the Linux Bridge
        brctl = '/sbin/brctl'
        ifconfig = '/sbin/ifconfig'

        cmds = [
            "%s delbr %s",
            "%s addbr %s"
        ]

        map(lambda s: quietRun(s % (brctl, self.name)), cmds)

        for intf in self.intfs.values():
            #don't do this, it will remove the qdiscs :(
            #quietRun("%s %s down" % (ifconfig, intf))
            quietRun("%s addif %s %s" % (brctl, self.name, intf))

        quietRun("%s %s up" % (ifconfig, self.name))

        for intf in self.intfs.values():
            quietRun("%s %s up" % (ifconfig, intf))

    def stop(self):
        ifconfig = '/sbin/ifconfig'
        quietRun("%s %s down" % (ifconfig, self.name))
        self.deleteIntfs()
