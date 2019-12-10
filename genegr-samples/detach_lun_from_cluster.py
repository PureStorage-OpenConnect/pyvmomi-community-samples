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
 Simple pyVmomi program for detaching a LUN from all ESXi nodes of a cluster
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

    parser.add_argument('-D', '--datacenter',
                        required=True,
                        action='store',
                        help='datacenter name')

    parser.add_argument('-C', '--cluster',
                        required=True,
                        action='store',
                        help='cluster name')

    parser.add_argument('-l', '--lunuuid',
                        required=True,
                        action='store',
                        help='lun UUID')

    args = parser.parse_args()

    return cli.prompt_for_password(args)


def main():
    """
    Simple command-line program for detaching a LUN from all the ESXi hosts
    of a cluster
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

        # Get datacenter view
        objview = content.viewManager.CreateContainerView(content.rootFolder,
                                                          [vim.Datacenter],
                                                          True)
        datacenters = objview.view
        objview.Destroy()

        # Retrieve datacenter
        datacenter = None
        for dc in datacenters:
            if dc.name == args.datacenter:
              datacenter = dc
              break
        if (datacenter is None):
            print ("datacenter " + args.datacenter + " not found")
            return -1
          
        # Retrieve cluster
        cluster = None
        for ce in datacenter.hostFolder.childEntity:
            if ce.name == args.cluster:  
                cluster = ce
                break
        if (cluster is None):
            print ("cluster " + args.cluster + " not found")
            return -1


        for eh in cluster.host:
            storage_system = eh.configManager.storageSystem
            print ("Detaching SCSI lun " + args.lunuuid + " from cluster node " + eh.name)
            storage_system.DetachScsiLun(args.lunuuid)

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0

# Start program
if __name__ == "__main__":
    main()
