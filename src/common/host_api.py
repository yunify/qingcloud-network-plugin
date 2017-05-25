import abc

import six


@six.add_metaclass(abc.ABCMeta)
class HostBaseDriver(object):
    """Define stable abstract interface for Host driver.

    A Host driver is called on the creation and deletion of bm host
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
