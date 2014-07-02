#!/usr/bin/env python

import argparse
import logging
import sys
import suds

import nogvmware.util as u

from psphere.managedobjects import VirtualMachine

logging.basicConfig(level=logging.INFO)

class StopVM(u.Client, u.Tasker):

    def __init__(self, args):
        self.vms = args.vm
        self.force = args.force
        u.Client.__init__(self)

    def run(self):
        for vm in self.vms:
            self.stop(vm)

    def stop(self, vmname):
        vm = VirtualMachine.get(self.client, name=vmname)
        print 'Attempting to shut down ' + vmname
        try:
            shutdown = vm.ShutdownGuest()
            self.task(vm, shutdown)
        except suds.WebFault as e:
            if self.force:
                print 'Attempting to forcefully power off ' + vmname
                pass
            else:
                raise e
        print 'Attempting to power off ' + vmname
        poweroff = vm.PowerOffVM_Task()
        self.task(vm, poweroff)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('vm', nargs='+', help='Names of virtual machines to shut down')
    parser.add_argument('-f', dest='force', action='store_const', const=True, default=False, help='Forceful and sudden shutdown')
    args = parser.parse_args()
    stopvm = StopVM(args)
    return stopvm.run()

if __name__ == '__main__':
    sys.exit(main())
