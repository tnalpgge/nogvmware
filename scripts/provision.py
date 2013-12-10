#!/usr/bin/env python

import argparse
import logging
import sys
import time

from psphere import config #, template
from psphere.client import Client
#from psphere.errors import TemplateNotFoundError
from psphere.managedobjects import ComputeResource
from psphere.soap import VimFault

import nogvmware.util as u

logging.basicConfig(level=logging.INFO)

class Provision(u.Client, u.Tasker):

    def __init__(self, args):
        self.hotplug = args.hotplug
        self.coldplug = args.coldplug
        self.memory = args.memory
        self.cpu = args.cpu
        self.disks = args.disksize
        self.nics = args.nic
        self.isofile = args.iso
#        self.tmplname = args.template
        self.server = config._config_value('general', 'server', args.server)
        self.username = config._config_value('general', 'username', args.username)
        self.password = config._config_value('general', 'password', args.password)
        self.crname = args.compute_resource
        self.hostname = args.host
        self.dsname = args.datastore
        self.thick_disks = args.thick_disks
        self.name = args.name
        self.guestid = args.guest_id
#        self.template = None
        self.resource_pool = None
        self.diskctlr = None
        self.datastore = None
        self.datacenter = None
        self.target = None
        self.devices = []
        self.vmdisks = []
        self.vmnics = []
        self.unit = 0
        self.key = 0
        self.cdrom = None
        u.Client.__init__(self)

    def next_key(self):
        x = self.key
        self.key = self.key + 1
        return x

    def next_unit(self):
        x = self.unit
        self.unit = self.unit + 1
        return x

    def validate(self):
        if self.server is None:
            raise ValueError('server must be supplied on command line or in config file')
        if self.username is None:
            raise ValueError('username must be supplied on command line or in config file')
        if self.password is None:
            raise ValueError('password must be supplied on command line or in config file')
        if self.hotplug and self.coldplug:
            raise ValueError('hotplug and coldplug are mutually exclusive')
        if self.memory <= 0:
            raise ValueError('memory must be positive')
        if self.cpu <= 0:
            raise ValueError('number of CPUs must be positive')
        if self.disks is None:
            raise IndexError('must specify at least one disk')
        if self.nics is None:
            raise IndexError('must specify at least one network interface')
        for disk in self.disks:
            if disk < 0:
                raise ValueError('disk size must be positive')
#        if self.tmplname is not None:
#            try:
#                self.template = template.load_template(self.tmplname)
#            except TemplateNotFoundError:
#                raise ValueError('Template %s could not be found' % (self.tmplname))

    def identify_resource_pool(self):
        if self.hostname is not None:
            logging.info('finding resource pool by host name')
            self.target = self.client.find_entity_view('HostSystem', filter={'name': self.hostname})
            self.resource_pool = target.parent.resourcePool
            self.datacenter = self.target.parent.parent.parent
        elif self.crname is not None:
            logging.info('finding resource pool by compute resource')
            self.target = self.client.find_entity_view('ComputeResource', filter={'name': self.crname})
            self.resource_pool = self.target.resourcePool
            self.datacenter = self.target.parent.parent
        else:
            logging.info('using first compute resource for resource pool')
            crs = ComputeResource.all(self.client)
            self.target = crs[0]
            print 'Defaulting to first ComputeResource %s' % (self.target.name)
            self.resource_pool = self.target.resourcePool
            self.datacenter = self.target.parent.parent

    def identify_datastore(self):
        if self.dsname is not None:
            logging.info('finding data store by name')
            for datastore in self.target.datastore:
                if datastore.name == self.dsname:
                    self.datastore = datastore
                    break
        else:
            logging.info('using first data store')
            try:
                self.datastore = self.target.datastore[0]
                print 'Defaulting to first Datastore %s' % (self.datastore.summary.name)
            except IndexError:
                pass
        if self.datastore is None:
            raise ValueError('No datastore in %s with name %s' % (self.resource_pool.name, self.dsname))
        if self.datastore.summary.accessible is not True:
            raise ValueError('Datastore %s is not accessible' % (self.datastore.summary.name))

    def disk_controller(self):
        logging.info('creating disk controller')
        controller = self.client.create('VirtualLsiLogicController')
        controller.key = self.next_key()
        controller.device = [0]
        controller.busNumber = (0,)
        controller.sharedBus = self.client.create('VirtualSCSISharing').noSharing
        spec = self.client.create('VirtualDeviceConfigSpec')
        spec.device = controller
        spec.fileOperation = None
        spec.operation = self.client.create('VirtualDeviceConfigSpecOperation').add
        self.diskctlr = spec
        self.devices.append(self.diskctlr)

    def create_vmcdrom(self):
        logging.info('creating cdrom')
        cdrom = self.client.create('VirtualCdrom')
        cdrom.key = self.next_key()
        # hate magic, unexplained numbers
        cdrom.controllerKey = 201
        cdrom.unitNumber = 0
        desc = self.client.create('Description')
        desc.label = 'CD-ROM device cdrom0'
        desc.summary = 'key %d controllerKey %d unitNumber %d' % (cdrom.key, cdrom.controllerKey, cdrom.unitNumber)
        cdrom.deviceInfo = desc
        vdci = self.client.create('VirtualDeviceConnectInfo')
        vdci.startConnected = True
        vdci.allowGuestControl = False
        if self.isofile:
            iso = self.client.create('VirtualCdromIsoBackingInfo')
            iso.fileName = self.isofile
            iso.datastore = self.datastore
            vdci.connected = True
            cdrom.backing = iso
        else:
            cdrom.backing = None
            vdci.connected = False
        cdrom.connectable = vdci
        spec = self.client.create('VirtualDeviceConfigSpec')
        spec.device = cdrom
        spec.fileOperation = None
        specop = self.client.create('VirtualDeviceConfigSpecOperation')
        spec.operation = specop.add
        self.cdrom = spec
        self.devices.append(self.cdrom)

    def create_vmdisk(self, disksize):
        logging.info('creating disk unit %d size %d', self.unit, disksize)
        backing = self.client.create('VirtualDiskFlatVer2BackingInfo')
        backing.datastore = None
        backing.diskMode = 'persistent'
        backing.fileName = '[%s]' % self.datastore.summary.name
        backing.thinProvisioned = not self.thick_disks
        disk = self.client.create('VirtualDisk')
        disk.backing = backing
        disk.controllerKey = 0
        disk.key = self.next_key()
        disk.unitNumber = self.unit
        disk.capacityInKB = disksize * 1024 * 1024
        spec = self.client.create('VirtualDeviceConfigSpec')
        spec.device = disk
        specfileop = self.client.create('VirtualDeviceConfigSpecFileOperation')
        spec.fileOperation = specfileop.create
        specop = self.client.create('VirtualDeviceConfigSpecOperation')
        spec.operation = specop.add
        self.vmdisks.append(spec)
        self.devices.append(spec)

    def allocate_disks(self):
        logging.info('allocate disks')
        freespace = self.datastore.summary.freeSpace
        requested = sum(self.disks) * 1024 * 1024
        if freespace < requested:
            raise ValueError('Insufficient free space on datastore %s (requested %d, actual %d)' % (self.datastore.summary.name, requested, freespace))
        for disk in self.disks:
            self.create_vmdisk(disk)
            self.unit = self.unit + 1

    def create_vmnic(self, vmnet):
        logging.info('creating nic unit %d network %s', self.unit, vmnet)
        networks = self.target.network
        thisnet = None
        for network in networks:
            if network.name == vmnet:
                thisnet = network
        if thisnet is None:
            raise ValueError('No network named %s' % (vmnet))
        backing = self.client.create('VirtualEthernetCardNetworkBackingInfo')
        backing.deviceName = vmnet
        backing.network = thisnet
        connect_info = self.client.create('VirtualDeviceConnectInfo')
        connect_info.allowGuestControl = True
        connect_info.connected = False
        connect_info.startConnected = True
        nic = self.client.create('VirtualE1000')
        nic.backing = backing
        nic.key = self.next_key()
        nic.unitNumber = self.next_unit()
        nic.addressType = 'generated'
        nic.connectable = connect_info
        spec = self.client.create('VirtualDeviceConfigSpec')
        spec.device = nic
        spec.fileOperation = None
        specop = self.client.create('VirtualDeviceConfigSpecOperation')
        spec.operation = specop.add
        self.vmnics.append(spec)
        self.devices.append(spec)

    def allocate_nics(self):
        logging.info('allocate nics')
        for vmnet in self.nics:
            self.create_vmnic(vmnet)

    def allocate_motherboard(self):
        logging.info('allocate motherboard')
        vmfi = self.client.create('VirtualMachineFileInfo')
        vmfi.vmPathName = '[%s]' % self.datastore.summary.name
        spec = self.client.create('VirtualMachineConfigSpec')
        spec.name = self.name
        spec.memoryMB = self.memory
        spec.files = vmfi
        spec.annotation = 'provision.py psphere'
        spec.numCPUs = self.cpu
        spec.guestId = self.guestid
        spec.deviceChange = self.devices
        self.vmspec = spec
        
    def launch_create_task(self):
        logging.info('attempting to launch creation task')
        logging.info(self.vmspec)
        task = self.datacenter.vmFolder.CreateVM_Task(config=self.vmspec, pool=self.resource_pool)
        self.task(None, task)
    
    def create_vm(self):
        logging.info('connecting to %s', self.server)
        self.identify_resource_pool()
        self.identify_datastore()
        self.disk_controller()
        self.allocate_disks()
        self.create_vmcdrom()
        self.allocate_nics()
        self.allocate_motherboard()
        self.launch_create_task()
        self.client.logout()

    def run(self):
        self.validate()
        self.create_vm()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--hotplug', action='store_true', default=False, help='Allow hot-plug/remove of CPU and memory')
    parser.add_argument('--coldplug', action='store_true', default=False, help='Permit CPU/memory changes only when powered off')
    parser.add_argument('--memory', type=int, help='Size of memory in MB')
    parser.add_argument('--cpu', type=int, help='Number of CPUs')

#    parser.add_argument('--template', default=None, help='Template used to create VM')
    parser.add_argument('--disksize', type=int, action='append', help='Size of disk in GB (repeatable)')
    parser.add_argument('--nic', action='append', help='Network to attach to interface (repeatable)')
    parser.add_argument('--server', default=None, help='Server to contact')
    parser.add_argument('--username', default=None, help='User name for authentication')
    parser.add_argument('--password', default=None, help='Password for authentication')
    parser.add_argument('--compute-resource', default=None, help='ComputeResource in which to provision new VM')
    parser.add_argument('--host', default=None, help='Host within ComputeResource to provision new VM')
    parser.add_argument('--datastore', help='Data store in which to provision new VM')
    parser.add_argument('--thick-disks', action='store_true', help='Thick provision disks (default is thin)')
    parser.add_argument('--guest-id', default='winXPProGuest', help='Brief description of guest OS')
    parser.add_argument('--iso', default=None, help='ISO image to attach to virtual CD-ROM')
    parser.add_argument('name', help='Name of new VM')
    args = parser.parse_args()
    provision = Provision(args)
    return provision.run()

if __name__ == '__main__':
    sys.exit(main())
