import uuid
import time

from cvprac.cvp_client import CvpClient
from cvprac.cvp_client_errors import CvpApiError


## TODO: Move all of these to a yaml config file
CVPHOST = ['10.81.111.8']
CVPUSER = 'cvpadmin'
CVPPW = 'cvp123'
TARGET = 'Ansible'
IMAGE = 'vEOS-4.17.2F-lab'
GW = '192.168.1.1'
SUBNET_MASK = '24'
##

def make_configlet(ip_addr):
    config = 'event-handler ansible-deploy\ntrigger on-boot\n'
    config += 'action ssh ansible-controller "ansible-playbook -i hosts deploy_leaf.yaml"\n'
    config += 'delay 120\nasynchronous\n!\n'
    
    config += 'hostname ansible-%s\n' % ip_addr
    config += 'ip route 0/0 %s\n!\n' % GW
    config += 'interface Management1\nip address %s/%s' \
               % (ip_addr, SUBNET_MASK)

    return config

def remove_old_configlet(name, cvpclnt):
    info = cvpclnt.api.get_configlet_by_name(name)
    cvpclnt.api.delete_configlet(name, info['key'])

def deploy_device(clnt, device, target_container, configlets, image=None):
    u_task_id = str(uuid.uuid1())
    # move to target container
    cont_info = clnt.api.get_container_by_name(target_container)

    task_info = 'Automated Task ID: %s' % u_task_id

    data = {'data': [{
                      'id': 1,
                      'info' : task_info,
                      'infoPreview': task_info,
                      'action': 'update',
                      'nodeId': device['key'],
                      'toId': cont_info['key'],
                      'fromId': 'undefined_container',
                      'nodeName': device['fqdn'],
                      'toName': cont_info['name'],
                      'toIdType': 'container',
                      'nodeType': 'netelement',
                      'childTasks': [],
                      'parentTask': ''}]}
    t = None
    try:
        print 'attemping to add move containter action'
        clnt.post('/provisioning/addTempAction.do?format=topology&queryParam=&nodeId=%s' % 'root',
                  data=data)
        
    except CvpApiError as e:
        if "Data already exists" in str(e):
            pass

        else:
            #unknown failure
            print "CvpAPi Error %s: exiting()..." % str(e)
    print 'done adding move containter action'    
    print 'getting proposed list of configlets'
    #get the proposed list of configlets
    prop_config = clnt.get('/provisioning/getTempConfigsByNetElementId.do?netElementId=%s' % device['key'])
    cl = [ c['key'] for c in prop_config['proposedConfiglets']]
    cnl = [ p['name'] for p in prop_config['proposedConfiglets']]
    
    #add in device specific configlets
    for config in configlets:
        cl.append(config['key'])
        cnl.append(config['name'])
 
    print 'done getting configlets'

    #apply all configlets to the device
    data = {'data': [{ 'id': 2, 
                       'info': task_info,
                       'infoPreview': task_info,
                       'note': '',
                       'action': 'associate',
                       'nodeType': 'configlet',
                       'nodeId': '',
                       'configletList': cl,
                       'configletNamesList': cnl,
                       'ignoreConfigletList': [],
                       'ignoreConfigletNamesList': [],
                       'configletBuilderList': [],
                       'configletBuilderNamesList': [],
                       'ignoreConfigletBuilderList': [],
                       'ignoreConfigletBuilderNamesList': [],
                       'toId': device['systemMacAddress'],
                       'toIdType':  'netelement',
                       'fromId': '',
                       'nodeName': '',
                       'fromName': '',
                       'toName': device['fqdn'],
                       'nodeIpAddress': device['ipAddress'],
                       'nodeTargetIpAddress': device['ipAddress'],
                       'childTasks': [],
                       'parentTask': '' }]}

    print 'trying to add configlets'
    clnt.post('/provisioning/addTempAction.do?format=topology&queryParam=&nodeId=%s' % 'root', data=data)
    print 'done with temp config add'
    
    if image:
        print 'trying to add image bundle'
        try:
            image_bundle = clnt.api.get_image_bundle_by_name(image)
        except CvpApiError as e:
            print 'issues with finding image bundle: %s exiting...' % str(e)
            exit()
        task = clnt.api.apply_image_to_device(image_bundle, device)
        print 'done with add action for image'

    else:
        # we are not using the imbedded save_topology call in the apply_image so we need to do it manually
        task = clnt.api._save_topology_v2([])

    return task





def main():
    clnt = CvpClient()
    clnt.connect(CVPHOST, CVPUSER, CVPPW)
    #get the devices in the undefined container

    inv = clnt.get('/inventory/getInventory.do?startIndex=0&endIndex=0')
    try:
        devices = [ k for k,v in inv['containerList'].iteritems() \
                    if v == 'Undefined'] 
    except KeyError:
        print 'no containers found...exiting...'
        exit()
    if len(devices) == 0:
        msg = 'No devices in undefined container.  Exiting'
        exit()
    else:
        node = None
        for device in devices:
            # get the device config:
            for element in inv['netElementList']:
                if element['key'] == device:
                    node = element       
                    break 
            #have the netElement need to make the ma1 configlet
            sn = node['systemMacAddress']
            configlet = make_configlet(node['ipAddress'])
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
                        print 'unable to add configlet %s' % str(e)

            #add ma1 configlet to device
            configlet_to_add = {'name':name, 'key':configlet_key}
            task = None
            task = deploy_device(clnt, node, TARGET, [configlet_to_add], IMAGE)   
            try:
                print 'attempting to execute task'
                clnt.api.execute_task(task['data']['taskIds'][0])
               
            except CvpApiError as e:
                print 'error executing task: %s' % str(e)
            print 'task executed...'

                                                     

if __name__ == '__main__':
    main()
