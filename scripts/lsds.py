#!/usr/bin/env python

import argparse
import logging
import os.path
import sys
import time

from psphere import config
from psphere.client import Client
from psphere.managedobjects import Datacenter

logging.basicConfig(level=logging.ERROR)

class ListDatastoreContents:
    
    def __init__(self, args):
        self.dcname = args.datacenter
        self.dsname = args.datastore
        self.server = config._config_value('general', 'server', args.server)
        self.username = config._config_value('general', 'username', args.username)
        self.password = config._config_value('general', 'password', args.username)
        self.client = None
        self.datacenter = None
        self.datastore = None


    def validate(self):
        pass

    def identify_datacenter(self):
        dcs = Datacenter.all(self.client)
        if self.dcname is None:
            self.datacenter = dcs[0]
            logging.info('defaulting to data center %s' % (self.datacenter.name))
        else:
            for dc in dcs:
                if dc.name == self.dcname:
                    self.datacenter = dc
                    break
            if self.datacenter is None:
                raise ValueError('no data center named %s' % (self.dcname))

    def identify_datastore(self):
        dss = self.datacenter.datastore
        if self.dsname is None:
            self.datastore = dss[0]
            logging.info('defaulting to data store %s' % (self.datastore.info.name))
        else:
            for ds in dss:
                if ds.info.name == self.dsname:
                    self.datastore = ds
                    break
            if self.datastore is None:
                raise ValueError('no data store named %s' % (self.dsname))

    def list_files(self):
        browser = self.datastore.browser
        rootpath = '[%s] /' % (self.datastore.info.name) 
        task = browser.SearchDatastoreSubFolders_Task(datastorePath=rootpath)
        while task.info.state == 'running':
            print '.',
            time.sleep(3)
            task.update()
        print 'done'
        for resultlist in task.info.result:
            # first entry is a type descriptor, skip over it
            for result in resultlist[1:]:
                for r in result:
                    try:
                        for f in r.file:
                            print os.path.join(r.folderPath, f.path)
                    except AttributeError:
                        pass

    def run(self):
        logging.info('connecting to %s', self.server)
        self.client = Client()
        self.identify_datacenter()
        self.identify_datastore()
        self.list_files()
        self.client.logout()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', default=None, help='Server to contact')
    parser.add_argument('--username', default=None, help='User name for authentication')
    parser.add_argument('--password', default=None, help='Password for authentication')
    parser.add_argument('--datacenter', default=None, help='Name of data center to query')
    parser.add_argument('--datastore', default=None, help='Name of data store to query')
    args = parser.parse_args()
    lsds = ListDatastoreContents(args)
    return (lsds.run())

if __name__ == '__main__':
    sys.exit(main())
