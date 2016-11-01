#!/usr/bin/env python

DOCUMENTATION = """
---
module: cv_info
version_added: "2.2"
author: "EOS+ CS (ansible-dev@arista.com)"
short_description: Gather Information about Cloudvision node.
description:
  - Gathers basic information about a Cloudvision instance. This module will
    return the version of Cloudvision that is running.
options:
  host:
    description:
      - The ip address or hostname of the Cloudvision server.
    required: true
    default: null
  username:
    description:
      - The username to log into Cloudvision.
    required: true
    default: null
  password:
    description:
      - The password to log into Cloudvision.
    required: true
    default: null
  protocol:
    description:
      - The HTTP protocol to use. Choices include http and https.
    required: false
    default: https
  port:
    description:
      - The HTTP port to use. The defaults for http and https will be used
        if none is specified.
    required: false
    default: null
"""
from ansible.module_utils.basic import AnsibleModule
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


def gather_cv_info(module):
    return module.client.api.get_cvp_info()


def main():
    """ main entry point for module execution
    """
    argument_spec = dict(
        host=dict(required=True),
        port=dict(type='list', default=None),
        protocol=dict(default='https', choices=['http', 'https']),
        username=dict(required=True),
        password=dict(required=True),
    )

    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=False)

    result = dict(changed=False)

    module.client = connect(module)

    try:
        result['cvpInfo'] = gather_cv_info(module)
        result['changed'] = True
    except CvpApiError, e:
        module.fail_json(msg=str(e))

    module.exit_json(**result)


if __name__ == '__main__':
    main()
