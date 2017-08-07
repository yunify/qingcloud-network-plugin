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
    def get_routes(self, vpc_id):
        '''
        @param vpc_id: vpc to get static routes
        '''
        pass

    @abc.abstractmethod
    def add_route(self, vpc_id, destination, nexthop, device_name):

        '''
        @param vpc_id
        @param destination: ip network, eg: 0.0.0.0
        @param nexthop: gateway ip addr
        @param device_name: border device name to set bgp peer
        '''
        pass

    @abc.abstractmethod
    def delete_routes(self, vpc_id, destination=None):
        '''
        @param vpc_id: vpc to delete routes
        @param destination: destination route to delete. None to delete all
        '''
        pass

    @abc.abstractmethod
    def create_direct_port(self, user_id, vxnet_id,
                           switch_name, interface_name,
                           ip_address, vlan_id):
        pass
