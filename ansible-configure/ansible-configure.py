#
# Copyright (c) 2017, Arista Networks, Inc.
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

import yaml
import argparse
import subprocess
import logging

from cvprac.cvp_client import CvpClient
from cvprac.cvp_client_errors import CvpApiError

logging.basicConfig(filename='/tmp/ansible_cvp.log', level=logging.DEBUG, 
                    format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

def move_to_container(clnt, device, name):
    task = None
    # get container info
    c_info = clnt.api.get_container_by_name(name)
    # schedule move
    task = clnt.api.move_device_to_container('Ansible Deploy', device, c_info, True)
    return task 

def main():
    parser = argparse.ArgumentParser(description="Auto Provision CVP Nodes with Ansible")
    parser.add_argument("--config", action="store", help="config file location",
                                          default="config.yml")
    options = parser.parse_args()

    try:
        with open(options.config) as f:
            config = yaml.safe_load(f)
    except IOError:
        logging.info(Config file %s not found' % options.config)
        exit()

    clnt = CvpClient()
    try:
        clnt.connect(config['cvp_host'], config['cvp_user'], config['cvp_pw'])
    except KeyError:
        logging.info("CVP Credentials not found in config file")
        exit()    
                   
    # determine if there is any nodes in the ansible container
    try:
       target = config['target_container']
       prov_cont = config['provisioned_container']
    except KeyError:
       logging.info("Not container info found in config file")
       exit()
     
    try:
        verbosity = config['verbosity']
    except KeyError:
        verbosity = 'v';
    try:
        ansible_path = config['ansible_path']
    except:
        ansible_path = '/usr/bin/ansible'
                     
    devices = clnt.api.get_devices_in_container(target)
     
    for to_provision in devices:
        # move the container
        task = move_to_container(clnt, to_provision, prov_cont) 
        #cancel the task so we don't lose configs
        clnt.api.cancel_task(task['data']['taskIds'][0])
 
        # create dynamic host file
        with open('cvp_provision', 'w+') as f:
            f.write('%s  ansible_host=%s' % (to_provision['fqdn'], to_provision['ipAddress']))
                     
        logging.info("Starting to configure %s" % to_provision['fqdn'])
                     
        try:
            logging.info("Staring to configure %s via Ansible" % to_provision['fqdn'])
            output = subprocess.check_output([ansible_path, '-i', "-%s" % verbosity, 
                                              'cvp_provision', config['playbook']])
            logging.info(output)
            logging.info("Ansible completed configuration")
                     
        except subprocess.CalledProcessError as e:
            logging.info("Ansible provision failed for host %s due to %s" % i(fqdn, str(e)))
            # Ansible errored out so move device back
            task = move_to_container(clnt, to_provision, target) 
            #cancel the task so we don't lose configs
            clnt.api.cancel_task(task['data']['taskIds'][0])
            continue

if __name__ == '__main__':
    main()
