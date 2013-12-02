
import sys
from twisted.python import log
log.startLogging(sys.stdout, setStdout=False)
from trigger.cmds import Commando
import xml.etree.cElementTree as ET

class ConfigFetcher(Commando):
    vendors = ['paloalto', 'juniper', 'aruba', 'netscreen', 'cisco', 'force10']
    config_map = {
        'juniper': 'show configuration',
        'paloalto': 'show config running',
        'aruba': 'show configuration',
    }

    def from_base(self, results, device):
        """Call store_results without calling the default of map_results"""
        log.msg('Received %r from %s' % (results, device))
        self.store_results(device, results)

    def _ioslike(self):
        return ['show running-config']

    def to_base(self, device, commands=None, extra=None):
        commands = commands or self.commands
        if device.is_ioslike():
            return self._ioslike()
        log.msg('Sending %r to %s' % (commands, device))
        return commands

    def to_juniper(self, device, commands=None, extra=None):
        if self.force_cli:
            return ['show configuration']
        elem = ET.Element('get-configuration', database='committed',
                          inherit='inherit')
        self.commands = [elem]
        return self.commands

    def to_aruba(self, device, commands=None, extra=None):
        return ['show configuration']

    def to_netscreen(self, device, commands=None, extra=None):
        return ['get config']
