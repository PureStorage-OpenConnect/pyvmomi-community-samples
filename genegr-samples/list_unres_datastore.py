#!/usr/bin/env python

"""
Written by genegr
Github: https://github.com/genegr
Email: geneg@purestorage.com
Note: Example code For testing purposes only
This code has been released under the terms of the Apache-2.0 license
http://opensource.org/licenses/Apache-2.0
"""

"""

 Simple pyVmomi program for listing unresolved datastores and their
 associated devices

"""
from __future__ import print_function

from pyVim.connect import SmartConnect, SmartConnectNoSSL, Disconnect
from pyVmomi import vim, vmodl
from pyVim.task import WaitForTask
from tools import cli

import atexit
import sys

def get_args():
    parser = cli.build_arg_parser()

    args = parser.parse_args()
    return cli.prompt_for_password(args)

def main():
    """
    Simple command-line program for listing unresolved datastores and their
    associated devices
    """

 
    args = get_args()

    try:
        service_instance = None

        if args.disable_ssl_verification:
            service_instance = SmartConnectNoSSL(host=args.host,
                                                 user=args.user,
                                                 pwd=args.password,
                                                 port=443)
        else:
            service_instance = SmartConnect(host=args.host,
                                            user=args.user,
                                            pwd=args.password,
                                            port=443)

        if not service_instance:
            print("Could not connect to the specified host using specified "
                  "username and password")
            return -1

        atexit.register(Disconnect, service_instance)
        content = service_instance.RetrieveContent()

        # Search for all ESXi hosts
        objview = content.viewManager.CreateContainerView(content.rootFolder,
                                                          [vim.HostSystem],
                                                          True)
        esxi_hosts = objview.view
        objview.Destroy()

        for esxi_host in esxi_hosts:

            # All Filesystems on ESXi host
            storage_system = esxi_host.configManager.storageSystem
            host_unres_volumes = storage_system.QueryUnresolvedVmfsVolume()
            datastore_dict = {}
            # Map all filesystems
            for host_unres_vol in host_unres_volumes:
                print("{}\t{}\t\n".format("ESXi Host:    ", esxi_host.name))
                # Extract only VMFS volumes
                print(host_unres_vol.vmfsLabel)
                print("resolvable: %s" % (host_unres_vol.resolveStatus.resolvable))
                for ext in host_unres_vol.extent:
                    print("device path: %s" % (ext.devicePath))
                    print("startBlock: %d" % (ext.startBlock))
                    print("endBlock: %d" % (ext.endBlock))
                    

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0

# Start program
if __name__ == "__main__":
    main()
