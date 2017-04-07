# Ansible Role for Arista Cloudvision®
This repository contains several proof of concept scripts and modules that demonstrate the ability for CVP to integrate with other configuration management tools. This repository focuses specifically on CVP/Ansible integrations.

## Requirements
- [Arista Cloudvision (Version 2016.1.0 mimimum)](http://www.arista.com/en/products/eos/eos-cloudvision)
- [Cloudvision RestAPI Client (Version 0.7.0 minimum)](https://github.com/aristanetworks/cvprac)
- [Ansible (version 2.2 minimum)](https://github.com/ansible/ansible)

## Installation 
### Use Case 1: Ansible Controlled Configuration
#### Clone the ansible-cloudvision repo

```console
git clone https://github.com/arista-eosplus/ansible-cloudvision.git 
cd ansible-cloudvision
```
#### Setup the config.yml file from the auto_deploy script
```
cd auto_deploy
vi config.yml

---
cvp_host:
    - '<cvp host>'
cvp_user: <username>
cvp_pw: <password>
target_container: Ansible
provisioned_container: Provisioned
image: '<image bundle name>'
gw: '<default gateway address>'
subnet_mask: <subnet mask prefix len>
ansible_path: '<path to ansible-playbook>'
playbook: <playbook yaml file>

```

The `target_container` should match the name of the container thats configured for nodes to be placed in waiting after they have been bootrapped and are waiting for ansible to play a full configuration

The `provisoned_container` should match the name of the container thats configured for ansible-configure script to monitor

Note the same config file can be used for both the auto_deploy and the ansible_configure scripts

#### Install cronjobs 

The lines below will run the auto_deploy every minute and the ansible-configure script every 5 mintues
```console
* * * * * python /path/to/ansible-cloudvision/auto_deploy/auto_deploy.py
*/5 * * * * python /path/to/ansible-cloudvision/ansible_configure/ansible_configure.py
```

The `ansible_configure.py` script should be placed in the same directory with the playbook.  From there the normal Ansible convention can be used to obtain the neccesary needed for the configuration

### Use Case 2: Export CVP functionality to Ansible

#### Clone git repo
```console
git clone https://github.com/arista-eosplus/ansible-cloudvision.git
cd cvp_modules
```
#### Copy library/ and templates/ directory to local playbook directory
``` 
cp  library/ /path/to/ansible/playbook/
cp  templates/ /path/to/ansible/playbook/ 
```
At this point you will be able to use the cvp_server_provision module in the playbook run.
Please see the example test_server_provisoin.yml file for examples.

## Modules
### cv_info
Gather version information about Cloudvision

Returned object in the form:
```
{
  "cvpInfo": {
    "appVersion": "Phase_1.5_Sprint_25_HF_6",
    "version": "2016.1.2"
  }
}
```

### cv_inventory
Gather inventory about Cloudvision

Returned data in the form:
```
{
  "inventory": [
    {
      "architecture": "i386",
      "bootupTimeStamp": 1477935238.21,
      "complianceCode": null,
      "complianceIndication": "NONE",
      "deviceStatus": "Registered",
      "deviceStatusInfo": "Registered",
      "fqdn": "sw-172.30.1.1",
      "hardwareRevision": "",
      "internalBuildId": "e796e94c-ba3b-4355-afcf-ef0abfbfaee3",
      "internalVersion": "4.16.6M-3205780.4166M",
      "ipAddress": "172.30.1.1",
      "isDANZEnabled": "no",
      "isMLAGEnabled": "no",
      "key": "00:50:56:3a:c5:3e",
      "lastSyncUp": 0,
      "memFree": 97852,
      "memTotal": 1897592,
      "modelName": "vEOS",
      "serialNumber": "",
      "systemMacAddress": "00:50:56:3a:c5:3e",
      "taskIdList": [

      ],
      "tempAction": null,
      "type": "netelement",
      "unAuthorized": false,
      "version": "4.16.6M",
      "ztpMode": "true"
    }]
}
```

### cv_container
Add/Delete Modify Containers. If the parent container is not specified, the
root container, Tenant, will be used. The module will fail if the parent
container does not exist.

Example:
```
---
- hosts: cvp
  gather_facts: no
  connection: local

  tasks:
    - name: Create Container
      cv_container:
        host: "{{ cv_host }}"
        username: "{{ username }}"
        password: "{{ password }}"
        protocol: "{{ protocol }}"
        container: "newcontainer"
```

## Support

Please send questions to ansible-dev@arista.com.

## License

Copyright (c) 2017, Arista Networks EOS+
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

* Redistributions of source code must retain the above copyright notice,
  this list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright
  notice, this list of conditions and the following disclaimer in the
  documentation and/or other materials provided with the distribution.

* Neither the name of Arista Networks nor the names of its
  contributors may be used to endorse or promote products derived from
  this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
'AS IS' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL ARISTA NETWORKS
BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN
IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

