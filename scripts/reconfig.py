#!/usr/bin/env python

import argparse
import sys
import time

import nogvmware.util as u

from psphere.client import Client
from psphere.soap import VimFault
from psphere.managedobjects import VirtualMachine
from psphere.errors import ObjectNotFoundError

class ReconfigureVMs(u.Client, u.Tasker):

    def __init__(self, args):
        self.memory = args.memory
        self.cpu = args.cpu
        self.shutdown = args.shutdown
        self.reboot = args.reboot
        self.vms = args.vm
        self.hotplug = args.hotplug
        self.coldplug = args.coldplug
        self._config = None
        u.Client.__init__(self)

    def validate(self):
        if self.hotplug and self.coldplug:
            raise ArgumentError('Hot-plug and cold-plug are mutually exclusive')

    def create_config(self):
        new_config = self._client.create('VirtualMachineConfigSpec')
        if self.cpu is not None:
            new_config.numCPUs = self.cpu
        if self.memory is not None:
            new_config.memoryMB = self.memory
        if self.hotplug:
            new_config.cpuHotAddEnabled = True
            new_config.cpuHotRemoveEnabled = True
            new_config.memoryHotAddEnabled = True
        if self.coldplug:
            new_config.cpuHotAddEnabled = False
            new_config.cpuHotRemoveEnabled = False
            new_config.memoryHotAddEnabled = False
        self._config = new_config

    def reconfigure(self, vmname):
        try:
            vm = VirtualMachine.get(self._client, name=vmname)
            if self.shutdown:
                print 'Attempting to shut down %s' % (vmname)
                poweroff = vm.PowerOffVM_Task()
                self.task(vm, poweroff)
            print 'Attempting to reconfigure %s' % (vmname)
            reconfig = vm.ReconfigVM_Task(spec=self._config)
            self.task(vm, reconfig)
            if self.reboot:
                print 'Attempting to reboot %s' % (vmname)
                poweron = vm.PowerOnVM_Task()
                self.task(vm, poweron)
        except ObjectNotFoundError:
            print 'No VM found with name %s' % (vmname)
        except VimFault, e:
            print 'Task failed: %s' % (e)
        return


    def run(self):
        self.validate()
        self._client = Client()
        self.create_config()
        for vmname in self.vms:
            try:
                self.reconfigure(vmname)
            except Exception, e:
                print e
        self._client.logout()
        
        
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--memory', default=None, help='New memory in megabytes')
    parser.add_argument('--cpu', default=None, help='Number of CPUs')
    parser.add_argument('--shutdown', action='store_true', default=False, help='Shutdown VM before adjusting')
    parser.add_argument('--reboot', action='store_true', default=False, help='Reboot VM after adjusting')
    parser.add_argument('--hotplug', action='store_true', default=False, help='Allow hot-plug/remove of CPU and memory')
    parser.add_argument ('--coldplug', action='store_true', default=False, help='Permit CPU/memory changes only when powered off')
    parser.add_argument('vm', nargs='+', help='Names of virtual machines to modify')
    args = parser.parse_args()
    reconfig = ReconfigureVMs(args)
    return reconfig.run()

if __name__ == '__main__':
    sys.exit(main())
