#!/usr/bin/env python

import argparse
import sys

from psphere import config
from psphere.client import Client

class ListNetworks:

    def __init__(self, args):
        self.server = config._config_value('general', 'server', args.server)
        self.username = config._config_value('general', 'username', args.username)
        self.password = config._config_value('general', 'username', args.password)

    def validate(self):
        if self.server is None:
            raise ValueError('server must be supplied on command line or in config file')
        if self.username is None:
            raise ValueError('username must be supplied on command line or in config file')
        if self.password is None:
            raise ValueError('password must be supplied on command line or in config file')

    def run(self):
        client = Client()
        hsev = client.find_entity_view('HostSystem', filter={'name': self.server})
        for network in hsev.network:
            print network.name
        client.logout()
        
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', default=None, help='Server to contact')
    parser.add_argument('--username', default=None, help='User name for authentication')
    parser.add_argument('--password', default=None, help='Password for authentication')
    args = parser.parse_args()
    lsnets = ListNetworks(args)
    return lsnets.run()

if __name__ == '__main__':
    sys.exit(main())
        
