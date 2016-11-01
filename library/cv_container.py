#!/usr/bin/env python

DOCUMENTATION = """
---
module: cv_info
version_added: "2.2"
author: "EOS+ CS (ansible-dev@arista.com)"
short_description: Gather Information about Cloudvision node.
description:
  - Arista EOS configurations use a simple block indent file syntax
    for segmenting configuration into sections.  This module provides
    an implementation for working with eos configuration sections in
    a deterministic way.  This module works with either CLI or eAPI
    transports.
options:
  lines:
    description:
      - The ordered set of commands that should be configured in the
        section.  The commands must be the exact same commands as found
        in the device running-config.  Be sure to note the configuration
        command syntax as some commands are automatically modified by the
        device config parser.
    required: false
    default: null
"""
from ansible.module_utils.basic import AnsibleModule
from cvprac.cvp_api import CvpApi
from cvprac.cvp_client import CvpClient
from cvprac.cvp_client_errors import CvpLoginError, CvpApiError


def connect(module):
    client = CvpClient()
    try:
        client.connect([module.params['host']],
                       module.params['username'],
                       module.params['password'],
                       protocol=module.params['protocol'],
                       port=module.params['port'],
                       )
    except CvpLoginError, e:
        module.fail_json(msg=str(e))

    return client


def get_containers(client):
    url = '/inventory/add/searchContainers.do?startIndex=0&endIndex=0'
    return client.get(url)

def process_container(module, container, parent):
    containers = get_containers(module.client)

    # Ensure the parent exists
    parent = next((item for item in containers['data'] if
                   item['name'] == parent), None)

    if not parent:
        module.fail_json(msg=str('Parent container does not exist.'))

    cont = next((item for item in containers['data'] if
                 item['name'] == container), None)

    if not cont:
        module.client.api.add_container(container,
                                        parent['name'],
                                        parent['id'])
        return True

    return False


def main():
    """ main entry point for module execution
    """
    argument_spec = dict(
        host=dict(required=True),
        port=dict(type='list', default=None),
        protocol=dict(default='https', choices=['http', 'https']),
        username=dict(required=True),
        password=dict(required=True),
        container=dict(required=True),
        parent=dict(default='Tenant'),
    )

    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=False)

    result = dict(changed=False)

    module.client = connect(module)
    container = module.params['container']
    parent = module.params['parent']

    try:
        changed = process_container(module, container, parent)
        if changed:
            result['changed'] = True
    except CvpApiError, e:
        module.fail_json(msg=str(e))

    module.exit_json(**result)


if __name__ == '__main__':
    main()
