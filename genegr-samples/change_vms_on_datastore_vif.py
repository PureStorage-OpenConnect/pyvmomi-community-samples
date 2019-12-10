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

 Simple pyVmomi program for changing the virtual NIC configuration of a given VM

This program is mostly based on the Reubenur Rahman's change_vm_vif.py which is included in
the VMware pyvmomi-community-samples GitHub project http://vmware.github.io/pyvmomi-community-samples/

"""

from __future__ import print_function

from pyVim.connect import SmartConnect, SmartConnectNoSSL, Disconnect
from pyVmomi import vim, vmodl
from pyVim.task import WaitForTask
from tools import cli

import atexit
import sys
import csv

def get_obj(content, vimtype, name):
    """
     Get the vsphere object associated with a given text name
    """
    obj = None
    container = content.viewManager.CreateContainerView(content.rootFolder,
                                                        vimtype, True)
    for view in container.view:
        if view.name == name:
            obj = view
            break
    return obj

def get_args():
    """
     Get command line args from the user.
    """

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


    parser.add_argument('-m', '--network_map',
                        required=True,
                        action='store',
                        help='comma separated file of network mapping, with the following columns: src-dvswith-uuid,src-dportgroup-key,dst-portgroup-name')

    args = parser.parse_args()

    return cli.prompt_for_password(args)

def main():
    """
     Simple command-line program for changing network virtual machines NIC.
    """

    args = get_args()

    try:

        # Read network mapping
        with open(args.network_map, 'rb') as csvfile:
            reader = csv.DictReader(csvfile, fieldnames=['src_dvs_uuid','src_dpg_key','src_type','dst_net','dst_type'])
            network_map = list(reader)
            csvfile.close()

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

        for vm in vm_view.view:
            for d in vm.datastore:
                if not d.name == args.datastore:
                    # vm is not on our datastore
                    continue

            device_change = []
            # Iterate over all the vNIC's of a VM
            for device in vm.config.hardware.device:
                if isinstance(device, vim.vm.device.VirtualEthernetCard):
                    for sw in network_map:
                        if sw['src_type'] == 'dvs' and isinstance(device.backing,
                                                                  vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo):
                            if not device.backing.port.switchUuid == sw['src_dvs_uuid']:
                                continue
                            if not device.backing.port.portgroupKey == sw['src_dpg_key']:
                                continue
                        elif sw['src_type'] == 'vs' and isinstance(device.backing,
                                                                   vim.vm.device.VirtualEthernetCard.NetworkBackingInfo):
                            if not device.deviceInfo.label == sw['src_dvs_uuid']:
                                continue
                            network = str(device.backing.network).strip("'")
                            if not network == sw['src_dpg_key']:
                                continue
                        else:
                            continue

                        # Here we have a vnic that matches the source network settings

                        nicspec = vim.vm.device.VirtualDeviceSpec()
                        nicspec.operation =  vim.vm.device.VirtualDeviceSpec.Operation.edit
                        nicspec.device = device
                        nicspec.device.wakeOnLanEnabled = True

                        if not sw['dst_type'] == 'dvs':
                            nicspec.device.backing =  vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
                            nicspec.device.backing.network =  get_obj(content, [vim.Network], sw['dst_net'])
                            nicspec.device.backing.deviceName = sw['dst_net']
                        else:
                            network = get_obj(content,
                                              [vim.dvs.DistributedVirtualPortgroup],
                                              sw['dst_net'])
                            dvs_port_connection = vim.dvs.PortConnection()
                            dvs_port_connection.portgroupKey = network.key
                            dvs_port_connection.switchUuid = \
                            network.config.distributedVirtualSwitch.uuid
                            nicspec.device.backing = \
                                vim.vm.device.VirtualEthernetCard. \
                                DistributedVirtualPortBackingInfo()
                            nicspec.device.backing.port = dvs_port_connection

                        nicspec.device.connectable = \
                            vim.vm.device.VirtualDevice.ConnectInfo()
                        nicspec.device.connectable.startConnected = True
                        nicspec.device.connectable.allowGuestControl = True
                        device_change.append(nicspec)

                        config_spec = vim.vm.ConfigSpec(deviceChange=device_change)
                        try:
                            task = vm.ReconfigVM_Task(config_spec)
                            WaitForTask(task)
                            print("VM " + vm.name + " : successfully changed network for nic " + device.deviceInfo.label)
                        except Exception as e:
                            print("VM " + vm.name + " : error " + str(e))
     

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1

    return 0

# Start program
if __name__ == "__main__":
    main()
