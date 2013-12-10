#!/usr/bin/env python

import argparse
import logging
import sys

import nogvmware.util as u

from psphere.managedobjects import VirtualMachine

logging.basicConfig(level=logging.INFO)

class StopVM(u.Client, u.Tasker):

    def __init__(self, args):
        self.vms = args.vm
        u.Client.__init__(self)

    def run(self):
        for vm in self.vms:
            self.stop(vm)

    def stop(self, vmname):
        vm = VirtualMachine.get(self.client, name=vmname)
        print 'Attempting to shut down %s' % (vmname)
        shutdown = vm.ShutdownGuest()
        self.task(vm, shutdown)
        print 'Attempting to power off %s' % (vmname)
        poweroff = vm.PowerOffVM_Task()
        self.task(vm, poweroff)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('vm', nargs='+', help='Names of virtual machines to shut down')
    args = parser.parse_args()
    stopvm = StopVM(args)
    return stopvm.run()

if __name__ == '__main__':
    sys.exit(main())
