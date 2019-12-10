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

vSphere Python SDK program to register into inventory the VM's hosted on a specific datastore of a
given cluster in a given datacenter

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

        # Find the datastore we are using
        datastore = None
        datastores_object_view = content.viewManager.CreateContainerView(
                dc,
                [vim.Datastore],
                True)
        for ds in datastores_object_view.view:
            if  ds.info.name == args.datastore:
                datastore = ds
                break

        if not datastore:
            print("Could not find the datastore specified")
            raise SystemExit(-1)
        # Clean up the views now that we have what we need
        datastores_object_view.Destroy()
        datacenters_object_view.Destroy()

        # Search for all the vmx files on the datastore
        ds_path = '[' + datastore.name + ']'
        browser_spec = vim.host.DatastoreBrowser.SearchSpec()
        browser_spec.matchPattern = ['*.vmx']
        task = datastore.browser.SearchDatastoreSubFolders_Task(datastorePath=ds_path, searchSpec=browser_spec)
        WaitForTask(task)
        
        # Build the list of retrieved vmx files
        vmx_files = []
        for res in task.info.result:
            vmx_files.append(res.folderPath + '/' + res.file[0].path)


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

        if not cluster:
            print("Could not find the cluster specified")
            raise SystemExit(-1)

        # Register all the VMs that have a vmx file on the datastore
        for p in vmx_files:
            task=datacenter.vmFolder.RegisterVM_Task(path=p, asTemplate=False, pool=cluster.resourcePool)
            WaitForTask(task)
            print("Succefully registered VM " + task.info.result.config.name + " with instance uuid=" + task.info.result.config.instanceUuid + "and uuid=" + task.info.result.config.uuid)


    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0



# Start program
if __name__ == "__main__":
    main()
