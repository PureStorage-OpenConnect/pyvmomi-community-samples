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

 Simple pyVmomi program for registerin a VM on a cluster of a given datacenter
 from a vmx file.

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
                        help='Datastore name')

    parser.add_argument('-C', '--cluster',
                        required=True,
                        action='store',
                        help='Datastore name')

    parser.add_argument('-f', '--vmxpath',
                        required=True,
                        action='store',
                        help='vmx file path')

    args = parser.parse_args()

    return cli.prompt_for_password(args)




def main():
    """
    Simple command-line program for registering a VM from a datastore
    onto an ESXi host
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

        # Get the list of all datacenters we have available to us
        datacenters_object_view = content.viewManager.CreateContainerView(
            content.rootFolder,
            [vim.Datacenter],
            True)

        # Find the datastore and datacenter we are using
        datacenter = None
        cluster = None
        for dc in datacenters_object_view.view:
            if not dc.name == args.datacenter:
                continue
            datacenter = dc
            compute_res_view = content.viewManager.CreateContainerView(
                dc,
                [vim.ComputeResource],
                True)
            for cr in compute_res_view.view:
                if not cr.name == args.cluster:
                    continue
                cluster = cr


            
        
        # Clean up the views now that we have what we need
        datacenters_object_view.Destroy()
        compute_res_view.Destroy()


        task=datacenter.vmFolder.RegisterVM_Task(path=args.vmxpath, asTemplate=False, pool=cluster.resourcePool)
        WaitForTask(task)
        print(task.info.result.config.name)
        print(task.info.result.config.instanceUuid)
        print(task.info.result.config.uuid)

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0



# Start program
if __name__ == "__main__":
    main()
