#!/usr/bin/env python
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
DOCUMENTATION = """
---
module: cv_server_provision
version_added: "2.2"
author: "EOS+ CS (ansible-dev@arista.com)"
short_description:
  - Provision server port by applying or removing template
    configuration to configlet.
description:
  - This module allows a server team to provision server network ports for
    new servers without having to access Arista CVP or asking the network team
    to do it for them. Provide the information for connecting to CVP, switch
    rack, port the new server is connected to, optional vlan, and an action
    and the module will apply the configuration to the switch port via CVP.
    Actions are add (applies template config to port),
    remove (defaults the interface config) and
    present (returns the current port config).
options:
  host:
    description:
    required:
    default:
  port:
    description:
    required:
    default:
  protocol:
    description:
    required:
    default:
  username:
    description:
    required:
    default:
  password:
    description:
    required:
    default:
  server_name:
    description:
    required:
    default:
  switch_name:
    description:
    required:
    default:
  switch_port:
    description:
    required:
    default:
  port_vlan:
    description:
    required:
    default:
  template:
    description:
    required:
    default:
  state:
    description:
    required:
    default:
  auto_run:
    description:
    required:
    default:
"""

import re
import time
from jinja2 import meta
import jinja2

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


def switch_info(module):
    # Ensure the switch exists
    switch_name = module.params['switch_name']
    switch_info = module.client.api.get_device_by_name(switch_name)
    if not switch_info:
        module.fail_json(msg=str("Device with name '%s' does not exist."
                                 % switch_name))
    return switch_info


def switch_in_compliance(module, sw_info):
    compliance = module.client.api.check_compliance(sw_info['key'],
                                                    sw_info['type'])
    if compliance['complianceCode'] != '0000':
        module.fail_json(msg=str('Switch %s is not in compliance. Returned'
                                 ' compliance code %s.'
                                 % (sw_info['fqdn'],
                                    compliance['complianceCode'])))


def server_configurable_configlet(module):
    switch_name = module.params['switch_name']
    device_info = module.client.api.get_device_by_name(switch_name)
    if not device_info:
        module.fail_json(msg=str("Device with name '%s' does not exist."
                                 % switch_name))
    configlet_name = switch_name + '-server'
    switch_configlets = module.client.api.get_configlets_by_device_id(
        device_info['key'])
    for configlet in switch_configlets:
        if configlet['name'] == configlet_name:
            return configlet
    return None


def port_configurable(module, configlet):
    regex = r'^interface Ethernet%s' % module.params['switch_port']
    for config_line in configlet['config'].split('\n'):
        if re.match(regex, config_line):
            return True
    return False


def configlet_action(module, configlet):
    result = dict()
    existing_config = current_config(module, configlet['config'])
    if module.params['state'] == 'present':
        result['currentConfigBlock'] = existing_config
        return result
    elif module.params['state'] == 'add':
        result['newConfigBlock'] = config_from_template(module)
    elif module.params['state'] == 'remove':
        result['newConfigBlock'] = ('interface Ethernet%s\n!'
                                    % module.params['switch_port'])
    result['oldConfigBlock'] = existing_config
    result['fullConfig'] = updated_configlet_content(module,
                                                     configlet['config'],
                                                     result['newConfigBlock'])
    resp = module.client.api.update_configlet(result['fullConfig'],
                                              configlet['key'],
                                              configlet['name'])
    if 'data' in resp:
        result['updateConfigletResponse'] = resp['data']
        if 'task' in resp['data']:
            result['changed'] = True
            result['taskCreated'] = True
    return result


def current_config(module, config):
    regex = r'^interface Ethernet%s' % module.params['switch_port']
    match = re.search(regex, config, re.M)
    if not match:
        module.fail_json(msg=str('interface section not found - %s'
                                 % config))
    block_start, line_end = match.regs[0]

    match = re.search(r'!', config[line_end:], re.M)
    if not match:
        return config[block_start:]
    _, block_end = match.regs[0]

    block_end = line_end + block_end
    return config[block_start:block_end]


def valid_template(port, template):
    regex = r'^interface Ethernet%s' % port
    match = re.match(regex, template, re.M)
    if not match:
        return False
    return True


def config_from_template(module):
    template_loader = jinja2.FileSystemLoader('./templates')
    env = jinja2.Environment(loader=template_loader,
                             undefined=jinja2.DebugUndefined)
    template = env.get_template(module.params['template'])
    if not template:
        module.fail_json(msg=str('Could not find template - %s'
                                 % module.params['template']))

    data = {'switch_port': module.params['switch_port'],
            'server_name': module.params['server_name']}

    temp_source = env.loader.get_source(env, module.params['template'])[0]
    parsed_content = env.parse(temp_source)
    temp_vars = list(meta.find_undeclared_variables(parsed_content))
    if 'port_vlan' in temp_vars:
        if module.params['port_vlan']:
            data['port_vlan'] = module.params['port_vlan']
        else:
            module.fail_json(msg=str('Template %s requires a vlan. Please'
                                     ' re-run with vlan number provided.'
                                     % module.params['template']))

    template = template.render(data)
    if not valid_template(module.params['switch_port'], template):
        module.fail_json(msg=str('Template content does not configure proper'
                                 ' interface - %s' % template))
    return template


def updated_configlet_content(module, existing_config, new_config):
    regex = r'^interface Ethernet%s' % module.params['switch_port']
    match = re.search(regex, existing_config, re.M)
    if not match:
        module.fail_json(msg=str('interface section not found - %s'
                                 % existing_config))
    block_start, line_end = match.regs[0]

    updated_config = existing_config[:block_start] + new_config
    match = re.search(r'!\n', existing_config[line_end:], re.M)
    if match:
        _, block_end = match.regs[0]
        block_end = line_end + block_end
        updated_config += '\n%s' % existing_config[block_end:]
    return updated_config


def configlet_update_task(module):
    for num in range(3):
        device_info = switch_info(module)
        if (('taskIdList' in device_info) and
                (len(device_info['taskIdList']) > 0)):
            for task in device_info['taskIdList']:
                if ('Configlet Assign' in task['description'] and
                        task['data']['WORKFLOW_ACTION'] == 'Configlet Push'):
                    return task['workOrderId']
        time.sleep(1)
    return None


def wait_for_task_completion(module, task):
    task_complete = False
    while not task_complete:
        task_info = module.client.api.get_task_by_id(task)
        task_status = task_info['workOrderUserDefinedStatus']
        if task_status == 'Completed':
            return True
        elif task_status in ['Failed', 'Cancelled']:
            module.fail_json(msg=str('Task %s has reported status %s. Please'
                                     ' consult the CVP admins for more'
                                     ' information.' % (task, task_status)))
        time.sleep(2)


def main():
    """ main entry point for module execution
    """
    argument_spec = dict(
        host=dict(required=True),
        port=dict(type='list', default=None),
        protocol=dict(default='https', choices=['http', 'https']),
        username=dict(required=True),
        password=dict(required=True),
        server_name=dict(required=True),
        switch_name=dict(required=True),
        switch_port=dict(required=True),
        port_vlan=dict(required=False, default=None),
        template=dict(require=True),
        state=dict(default='present', choices=['present', 'add', 'remove']),
        auto_run=dict(default=False, choices=[True, False]),
    )

    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=False)
    result = dict(changed=False)
    module.client = connect(module)

    try:
        result['switchInfo'] = switch_info(module)
        if module.params['state'] in ['add', 'remove']:
            switch_in_compliance(module, result['switchInfo'])
        switch_configlet = server_configurable_configlet(module)
        if not switch_configlet:
            module.fail_json(msg=str('Switch %s has no configurable server'
                                     ' ports.' % module.params['switch_name']))
        result['switchConfigurable'] = True
        if not port_configurable(module, switch_configlet):
            module.fail_json(msg=str('Port %s is not configurable as a server'
                                     ' port on switch %s.'
                                     % (module.params['switch_port'],
                                        module.params['switch_name'])))
        result['portConfigurable'] = True
        result['taskCreated'] = False
        result['taskExecuted'] = False
        result['taskCompleted'] = False
        result.update(configlet_action(module, switch_configlet))
        if module.params['auto_run'] and module.params['state'] != 'present':
            task_id = configlet_update_task(module)
            if task_id:
                result['taskId'] = task_id
                note = ('Update config on %s with %s action from Ansible.'
                        % (module.params['switch_name'],
                           module.params['state']))
                module.client.api.add_note_to_task(task_id, note)
                module.client.api.execute_task(task_id)
                result['taskExecuted'] = True
                task_completed = wait_for_task_completion(module, task_id)
                if task_completed:
                    result['taskCompleted'] = True
            else:
                result['taskCreated'] = False
        result.update(module.params)
    except CvpApiError, e:
        module.fail_json(msg=str(e))

    module.exit_json(**result)


if __name__ == '__main__':
    main()
