# Ansible Role for Arista Cloudvision®
This repository contains several proof of concept scripts and modules that demonstrate the ability for CVP to integrate with other configuration management tools. This repository focuses specifically on CVP/Ansible integrations.

## Requirements
- [Arista Cloudvision](http://www.arista.com/en/products/eos/eos-cloudvision)
- [Cloudvision RestAPI Client](https://github.com/aristanetworks/cvprac)

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
