import yaml
import argparse
import subprocess

from cvprac.cvp_client import CvpClient
from cvprac.cvp_client_errors import CvpApiError

def move_to_provisioned_container(clnt, device, name):
    task = None
    # get container info
    c_info = clnt.api.get_container_by_name(name)
    # schedule move
    task = clnt.api.move_device_to_container('Ansible Deploy', device, c_info, True)
    return task
 

def main():
    parser = argparse.ArgumentParser(description="Auto Provision CVP Nodes with Ansible")
    parser.add_argument("--config", action="store", help="config file location",
                                          default="config.yml")
    options = parser.parse_args()

    try:
        with open(options.config) as f:
            config = yaml.safe_load(f)
    except IOError:
        print 'Config file %s not found' % options.config
        exit()

    clnt = CvpClient()
    clnt.connect(config['cvp_host'], config['cvp_user'], config['cvp_pw'])

    # determine if there is any nodes in the ansible container
    devices = clnt.api.get_devices_in_container(config['target_container'])
    fqdn = None
    ip = None
    to_provision = None 
    for device in devices:
        # get information about device
        inv = clnt.api.get_inventory()
        for node in inv:
            if node['systemMacAddress'] == device:
                to_provision = node
                break
        # move the container
        task = move_to_provisioned_container(clnt, to_provision, config['provisioned_container']) 
        #cancel the task so we don't lose configs
        clnt.api.cancel_task(task['data']['taskIds'][0])
 
        # create dynamic host file
        with open('cvp_provision', 'w+') as f:
            f.write('%s  ansible_host=%s' % (to_provision['fqdn'], to_provision['ipAddress']))
        print "Starting to configure %s" % fqdn
        try:
            output = subprocess.check_output([config['ansible_path'], '-i', 'cvp_provision', config['playbook']])
            print "Ansible completed configuration"
        except subprocess.CalledProcessError as e:
            print "Ansible provision failed for host %s due to %s" % i(fqdn, str(e))
            continue

            
        
if __name__ == '__main__':
    main()
