import abc

import six


@six.add_metaclass(abc.ABCMeta)
class QcExtBaseDriver(object):
    """Define stable abstract interface for QingCloud extension driver.

    including host and bgp management interface
    """

    @abc.abstractmethod
    def get_host(self, host):
        pass

    @abc.abstractmethod
    def delete_host(self, host):
        pass

    @abc.abstractmethod
    def create_host(self, host, mgmt_ip, connections):
        '''
        @param hostname: unique host name
        @param mgmt_ip: ip address in mgmt port, eg: ipmi
        @param connections: eg: [
        {
          "port": "port-channel103",
          "switchName": "Border-Leaf-92160.02"
        },
        {
          "port": "port-channel103",
          "switchName": "Border-Leaf-92160.01"
        }
      ]
        '''
        pass

    @abc.abstractmethod
    def add_router_bgp_peer(self, vpc_id, as_number, ip_address,
                            device_name):
        '''
        @param vpc_id
        @param as_number: bgp as number
        @param ip_address: ip addr in bgp interface
        @param device_name: border device name to set bgp peer
        '''
        pass

    @abc.abstractmethod
    def delete_router_bgp_peers(self, vpc_id):
        pass

    @abc.abstractmethod
    def create_direct_port(self, user_id, vxnet_id,
                           switch_name, interface_name,
                           ip_address, vlan_id):
        pass
