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

import re
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
    template_has_vlan = False
    if 'port_vlan' in temp_vars:
        template_has_vlan = True

    if template_has_vlan:
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
    device_info = switch_info(module)
    if ('taskIdList' in device_info) and (len(device_info['taskIdList']) > 0):
        for task in device_info['taskIdList']:
            if ('Configlet Assign' in task['description'] and
                    task['data']['WORKFLOW_ACTION'] == 'Configlet Push'):
                    return task['workOrderId']
    return None


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
        result.update(configlet_action(module, switch_configlet))
        if module.params['auto_run']:
            task_id = configlet_update_task(module)
            if task_id:
                result['taskId'] = task_id
                module.client.api.execute_task(task_id)
                result['taskExecuted'] = True
            else:
                result['taskCreated'] = False
        result.update(module.params)
    except CvpApiError, e:
        module.fail_json(msg=str(e))

    module.exit_json(**result)


if __name__ == '__main__':
    main()
