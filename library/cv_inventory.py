#!/usr/bin/env python
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


def gather_cv_inventory(module):
    return module.client.api.get_inventory()


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
        result['inventory'] = gather_cv_inventory(module)
        result['changed'] = True
    except CvpApiError, e:
        module.fail_json(msg=str(e))

    module.exit_json(**result)


if __name__ == '__main__':
    main()
