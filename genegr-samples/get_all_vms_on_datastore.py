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
 Simple pyVmomi program for retriving all the VMs located on a specific datastore and cluster
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

    parser.add_argument('-d', '--datastore',
                        required=True,
                        action='store',
                        help='Datastore name')

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

        atexit.register(Disconnect, service_instance)
        content = service_instance.RetrieveContent()

        # Get the list of all datacenters we have available to us
        datacenters_object_view = content.viewManager.CreateContainerView(
            content.rootFolder,
            [vim.Datacenter],
            True)

        # Find the datacenter we are using
        datacenter = None
        for dc in datacenters_object_view.view:
            if dc.name == args.datacenter:
                datacenter = dc
                break

        if not datacenter: 
            print("Could not find the datacenter specified")
            raise SystemExit(-1)


        # Find computeresource we are using
        cluster = None
        compute_res_view = content.viewManager.CreateContainerView(
                datacenter,
                [vim.ComputeResource],
                True)

        for cr in compute_res_view.view:
            if  cr.name == args.cluster:
                cluster = cr
                break

        # Clean up the view now that we have what we need
        compute_res_view.Destroy()
        datacenters_object_view.Destroy()

        if not cluster:
            print("Could not find the cluster specified")
            raise SystemExit(-1)

        vm_view = content.viewManager.CreateContainerView(
                cluster,
                [vim.VirtualMachine],
                True)

        print('#vm_name,instance_uuid,uuid')
        for vm in vm_view.view:
            for d in vm.datastore:
                if d.name == args.datastore:
                    print(vm.name + ',' + vm.config.instanceUuid + ',' + vm.config.uuid)
                    break

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0



# Start program
if __name__ == "__main__":
    main()
