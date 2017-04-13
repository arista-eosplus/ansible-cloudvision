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
import time
import yaml

from cvprac.cvp_client import CvpClient
from cvprac.cvp_client_errors import CvpApiError

def make_configlet(ip_addr, config):
    configlet = '' 
    configlet += 'hostname ansible-%s\n' % ip_addr
    configlet += 'ip route 0/0 %s\n!\n' % config['gw']
    configlet += 'interface Management1\nip address %s/%s' \
               % (ip_addr, config['subnet_mask'])

    return configlet

def remove_old_configlet(name, cvpclnt):
    info = cvpclnt.api.get_configlet_by_name(name)
    cvpclnt.api.delete_configlet(name, info['key'])

def main():
    parser = argparse.ArgumentParser(description="Auto Deploy CVP Nodes")
    parser.add_argument("--config", action="store", help="config file location",
                                          default="config.yml")
    options = parser.parse_args()

    try:
        with open(options.config) as f:
            config = yaml.safe_load(f)
    except IOError:
        print 'Config file %s not found' % options.config
        exit()

    clnt = CvpClient()
    clnt.connect(config['cvp_host'], config['cvp_user'], config['cvp_pw'])
    #get the devices in the undefined container
    devices = clnt.api.get_devices_in_container('Undefined') 

    if devices is None:
        print 'No devices in undefined container.  Exiting'
        exit()
    else:
        node = None
        for node in devices:
            print node
            #have the netElement need to make the ma1 configlet
            sn = node['systemMacAddress']
            configlet = make_configlet(node['ipAddress'], config)
            name = sn + '-MA1-CONFIG'
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
                        exit()

            #add ma1 configlet to device
            configlet_to_add = {'name':name, 'key':configlet_key}
            task = None
            print 'Attempting to deploy device %s' % node['systemMacAddress']
            try:
                task = clnt.api.deploy_device(node, config['target_container'], 
                                          [configlet_to_add], config['image'])   
                print 'Deploy Device task created'
                print 'Attempting to execute task'
                clnt.api.execute_task(task['data']['taskIds'][0])
                print 'Task executed...'
               
            except CvpApiError as e:
                print "unable to deploy: %s due to %s" % (node['systemMacAddress'], str(e))

if __name__ == '__main__':
    main()
