#
# Copyright (c) 2017, Arista Networks EOS+
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#   Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
#   Neither the name of Arista Networks nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# 'AS IS' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL ARISTA NETWORKS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN
# IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import argparse
import requests
import time
import yaml
import pyeapi

from cvprac.cvp_client import CvpClient
from cvprac.cvp_client_errors import CvpApiError

def validate_lldp(node, neigbor_info):
    node.enable(['show lldp neighbors detail'])
    # loop through the neighbor table and see if
    # matches what lldp says
    for i,v in neighbor_info.iteritems():
        try:
            int_neighbor = lldp[0]['result']['lldpNeighbors'][i]['lldpNeighborInfo'][0]
            neighbor_int = int_neighbor['neighborInterfaceInfo']['interfaceId']
            neighbor_name = int_neighbor['systemName']
            if neighbor_int != str(v['neighbor-port-id']) and \
               neighbor_name != str(v['neighbor-device-id']):
                   print 'in here for %s' % i
                   return {'msg': 'Interface %s has the incorrect LLDP Neigbhor\n' \
                                  'Neighbor Found is is %s and Neighbor port is %s' \
                                  % ( i, neighbor_name, neighbor_int),
                           'success': False}

        except KeyError:
            return {'msg':'No LLDP neighbors Found on interface %s' % i,
                    'success': False}
    #all interfaces match
    return {'msg':'', 'sucess':True}


def make_configlet(node_info, config):
    configlet = '' 
    configlet += 'hostname %s\n' % node_info.hostname
    configlet += 'ip route 0/0 %s\n!\n' % config['gw']
    configlet += 'ip domain-name %s\n!\n'  % config['fqdn']
    configlet += 'interface Management1\nip address %s/%s' \
               % (node_info.ip, config['subnet_mask'])

    return configlet


def remove_old_configlet(name, cvpclnt):
    info = cvpclnt.api.get_configlet_by_name(name)
    cvpclnt.api.delete_configlet(name, info['key'])

def find_node_match(cvp_node_detail, node_list):
    for node in node_list:
        if cvp_node_detail['systemMacAddress'].lower() == node.mac_addr.lower() and \
           cvp_node_detail['serialNumber'].lower() == node.sn.lower():
               return node
    # no match found
    return None

def wait_for_tasks(tasks, cvp):
    not_done = True
    while not_done:
        for task in tasks:
            status = cvp.api.get_task_by_id(task)
            if status['taskStatus'] == 'COMPLETED':
                not_done = False
            else:
                not_done = True
        print 'waiting for deploy tasks to complete...sleeping for 30 seconds..'
        time.sleep(30) 
    


class Node(object):
    def __init__(self, ip, sn, 
                 mac_addr, hostname, node_type ):
        self._ip = ip
        self._sn = sn
        self._mac_addr = mac_addr
        self._hostname = hostname
        self._node_type =  node_type

    def __repr__(self):
        return str(self.__dict__)

    @property
    def hostname(self):
        return self._hostname
    @property
    def node_type(self):
        return self._node_type

    @property
    def ip(self):
        return self._ip

    @property
    def sn(self):
        return self._sn

    @property
    def mac_addr(self):
        return self._mac_addr


def main():
    parser = argparse.ArgumentParser(description="Auto Deploy CVP Nodes")
    parser.add_argument("--config", action="store", help="config file location",
                                          default="config.yml")
    parser.add_argument("--info", action="store",
                        help="switch information yaml file",
                        default="basic-switch-info.yml")
    parser.add_argument("--lldp", action="store",
                        help="switch lldp yaml file",
                        default="basic-lldp-info.yml")
    parser.add_argument("--monitor", action="store_true",
                        help="make sure all tasks complete succesfully")
    

    options = parser.parse_args()
    info_nodes = []

    try:
        with open(options.config) as f:
            config = yaml.safe_load(f)
    except IOError:
        print 'Config file %s not found' % options.config
        exit(-1)
    try:
        with open(options.info) as i:
            fyi = yaml.safe_load(i)
    except IOError:
        print 'Info file %s not found' % options.info
        exit(-1)
    try:
        with open(options.lldp) as ld:
            neighbor_file = yaml.safe_load(ld)
    except IOError:
        print 'LLDP file %s not found' % options.lldp
        exit(-1)



    for info in fyi:
        for key, value in info.iteritems():
            if 'spine' in key.lower():
                node_type = 'SPINE'
            elif 'leaf' in key.lower():
                node_type = 'LEAF'
            try:
                info_nodes.append(Node(ip=value['mgmt-ip'], 
                                       sn=value['sn'],
                                       mac_addr=value['mac'],
                                       hostname=value['hostname'],
                                       node_type=node_type))
            except KeyError:
                print "%s did not have a required attribute (ip, sn, mac, or hostname)" % info


    clnt = CvpClient()
    clnt.connect(config['cvp_host'], config['cvp_user'], 
                 config['cvp_pw'], protocol='https')
    #get the devices in the undefined container
    devices = clnt.api.get_devices_in_container('Undefined') 
    no_matches = []
    nodes_with_tasks = []

    if devices is None:
        print 'No devices in undefined container.  Exiting'
        exit()
    else:
        node = None
        for node in devices:
            # try match a node in the undefinied container to informatin
            # in the info yaml file
            to_proceed = True
            match = find_node_match(node, info_nodes)  
            if match is not None:
                #have the netElement need to make the ma1 configlet
                sn = node['systemMacAddress']
                configlet = make_configlet(match, config)
                name = match.hostname + '-MA1-CONFIG'
                try:
                    configlet_key = clnt.api.add_configlet(name, configlet)
                except CvpApiError as e:
                    if 'Data already exists' in str(e):
                        #remove existing configlet and recreate
                        remove_old_configlet(name, clnt)
                        try:
                            configlet_key = clnt.api.add_configlet(name, configlet)
                        except CvpApiError as e:
                            # if this fails again tell user to check task list:
                            print 'unable to add configlet: %s' % str(e)
                            exit(-1)

                #add ma1 configlet to device
                configlet_to_add = {'name':name, 'key':configlet_key}
                tasks_to_monitor = []
                task = None
                print 'Attempting to deploy device %s' % node['systemMacAddress']
                # only send image if there is one in the config file
                try:
                    image = config['image']
                except KeyError:
                    image = None
                try:
                    # in this task it will move the node to the container 
                    # that matches the node_type 
                    task = clnt.api.deploy_device(node, match.node_type, 
                                              [configlet_to_add], image)   
                    print 'Deploy Device task created'
                    print 'Attempting to execute task'
                    clnt.api.execute_task(task['data']['taskIds'][0])
                    print 'Task executed...'
                    nodes_with_tasks.append(match)
                    tasks_to_monitor.append(task['data']['taskIds'][0])
                   
                except CvpApiError as e:
                    print "unable to deploy: %s due to %s" % (node['systemMacAddress'], str(e))
            else:
                print "no match found for %s" % node['systemMacAddress']
                no_matches.append(node)

        if options.monitor:
            wait_for_tasks(tasks_to_monitor, clnt)
            for sw in nodes_with_tasks:
                sw_lldp_info = (item for item in neighbor_file if item.keys()[0] == sw.hostname).next()
                host = sw_lldp_info.keys()[0]
                eapi_node = pyeapi.client.connect(host=host,
                                                  username=config['cvp_user'],
                                                  password=config['cvp_pw'],
                                                  return_node=True)
                cabling = validate_lldp(eapi_node, sw_lldp_info[host])
                if cabling['success']:
                    print 'LLDP Verified for  %s' % host
                else:
                    print 'LLDP error: %s for %s' % (cabling['msg'], host)

            
                 


if __name__ == '__main__':
    requests.packages.urllib3.disable_warnings()
    main()
