#!/usr/bin/env python

import argparse
import logging
import sys

import nogvmware.util as u

from psphere.managedobjects import VirtualMachine

logging.basicConfig(level=logging.INFO)

class StartVM(u.Client, u.Tasker):

    def __init__(self, args):
        self.vms = args.vm
        u.Client.__init__(self)

    def run(self):
        for vm in self.vms:
            self.start(vm)

    def start(self, vmname):
        vm = VirtualMachine.get(self.client, name=vmname)
        print 'Attempting to power on %s' % (vmname)
        poweron = vm.PowerOnVM_Task()
        self.task(vm, poweron)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('vm', nargs='+', help='Names of virtual machines to start')
    args = parser.parse_args()
    startvm = StartVM(args)
    return startvm.run()

if __name__ == '__main__':
    sys.exit(main())
