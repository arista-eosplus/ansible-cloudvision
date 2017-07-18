import pyeapi
import yaml

HOSTS = ['172.16.1.158', '172.16.1.16']


def validate_lldp(node, neighbor_info):
    '''runs through all the lldp neighbors for a given node
       returns a dict:
                   msg: Null of all interaces matches, reason if failure
                   success: True if all matches False if any fail
    '''
    lldp = node.enable(['show lldp neighbors detail'])
    # loop through the neighbor table and see if 
    # matches what lldp says
    valid = {}
    print neighbor_info
    for i,v in neighbor_info.iteritems():
        try:
            int_neighbor = lldp[0]['result']['lldpNeighbors'][i]['lldpNeighborInfo'][0]
            neighbor_int = int_neighbor['neighborInterfaceInfo']['interfaceId']
            neighbor_name = int_neighbor['systemName']
            if neighbor_int != str(v['neighbor-port-id']) and \
               neighbor_name != str(v['neighbor-device-id']):
                   print 'in here for %s' % i
                   return {'msg': 'Interface %s has the incorrect LLDP Neigbhor\n' \
                                  'Neighbor Found is is %s and Neighbor port is %s' \
                                  % ( i, neighbor_name, neighbor_int),
                           'success': False}

        except KeyError:
            return {'msg':'No LLDP neighbors Found on interface %s' % i,
                    'success': False}
    #all interfaces match
    return {'msg':'', 'sucess':True}

if __name__ == '__main__':
    with open('config.yml') as f:
        config = yaml.safe_load(f)
    with open('basic-lldp-dt.yml') as l:
        lldp_info = yaml.safe_load(l)
    for n in HOSTS:
        n_info = (item for item in lldp_info if item.keys()[0] == n).next()
        host= n_info.keys()[0]
        eapi_node = pyeapi.client.connect(host=host,
                                          username=config['cvp_user'],
                                          password=config['cvp_pw'],
                                          return_node=True)

        cabling = validate_lldp(eapi_node, n_info[host])
        print cabling


