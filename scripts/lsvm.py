#!/usr/bin/env python
# stolen from psphere example vidiscover.py and mercilessly kludged

import logging
import os.path
import sys

from psphere.scripting import BaseScript
from psphere.client import Client
from psphere.managedobjects import ComputeResource
from psphere.errors import ObjectNotFoundError

logging.basicConfig(level=logging.ERROR)

class ListVMs(BaseScript):

    def __init__(self, client):
        BaseScript.__init__(self, client)
        self.add_option('--compute-resource', dest='compute_resource', help='ComputeResource to display', required=False)
        self.config_vars = []
        self.visdkrc = os.path.expanduser(os.path.join('~', '.visdkrc'))

    def run(self):
        """An example that discovers hosts and VMs in the inventory."""
        # Find the first ClusterComputeResource
        ccr = None
        options = self.get_options()
        if options.compute_resource is None:
            logging.info('No compute resource specified, defaulting to first')
            cr_list = ComputeResource.all(self.client)
            options.compute_resource = cr_list[0]
        logging.info('Attempt to find compute resource %s', options.compute_resource.name)
        ccr = ComputeResource.get(self.client, name=options.compute_resource.name)
        print('Cluster: %s (%s hosts)' % (ccr.name, len(ccr.host)))
        ccr.preload("host", properties=["name", "vm"])
        print 'name\tcpu\tmemory\tguestId\tpowerState\tguestState'
        for host in ccr.host:
            logging.debug('preloading views for %s', host)
            # Get the vm views in one fell swoop
            host.preload("vm", properties=['name', 'config', 'runtime', 'guest'])
            for vm in host.vm:
                print '%s\t%d\t%d\t%s\t%s\t%s' % (vm.name, vm.config.hardware.numCPU, vm.config.hardware.memoryMB, vm.config.guestId, vm.runtime.powerState, vm.guest.guestState)
    
def main():
    client = Client()
    vd = ListVMs(client)
    vd.run()

if __name__ == '__main__':
    sys.exit(main())
