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
                        help='Datacenter name')

    parser.add_argument('-C', '--cluster',
                        required=True,
                        action='store',
                        help='Cluster name')

    parser.add_argument('-i', '--include_uplink',
                        required=False,
                        action='store_true',
                        help='vSwitch')

    args = parser.parse_args()

    return cli.prompt_for_password(args)


def main():
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

        atexit.register(Disconnect, service)instance)
        serviceContent = service_instance.RetrieveServiceContent()

        # Get the main datacenters view
        objview = serviceContent.viewManager.CreateContainerView(serviceContent.rootFolder,
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

        # Retrieve dvswitches and dvportgroups for this cluster
        dvsConfTgt = serviceContent.dvSwitchManager.QueryDvsConfigTarget(cluster.host[0])

        for dvpg in dvsConfTgt.distributedVirtualPortgroup:
            if dvpg.uplinkPortgroup  and  (not args.include_uplink):
                continue
            print (dvpg.switchName + "," + dvpg.switchUuid + ',' + dvpg.portgroupName + "," + dvpg.portgroupKey)

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0

# Main section
if __name__ == "__main__":
    sys.exit(main())
