from cvprac.cvp_client import CvpClient
from cvprac.cvp_client_errors import CvpApiError

CVPHOST = ['10.81.111.8']
CVPUSER = 'cvpadmin'
CVPPW = 'cvp123'
GW = '192.168.1.1'
SUBNET_MASK = '24'

def make_configlet(ip_addr):
    config = 'ip route 0/0 %s\n!\n' % GW
    config += 'interface Management1\nip address %s/%s' \
               % (ip_addr, SUBNET_MASK)

    return config

def remove_old_configlet(name, cvpclnt):
    info = cvpclnt.api.get_configlet_by_name(name)
    cvpclnt.api.delete_configlet(name, info['key'])


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
                configlet_key = clnt.api.add_configlet(name, configlet)
        #add ma1 configlet to device
        configlet_to_add = {'name':name, 'key':configlet_key}

        tasks = clnt.api.apply_configlets_to_device('Ansible',
                                                     node,
                                                     [configlet_to_add],
                                                   )
                                                     

if __name__ == '__main__':
    main()
