from oslo_log import log as logging
from networking_terra.common.client import TerraRestClient
from common.host_api import HostBaseDriver

LOG = logging.getLogger(__name__)


class TerraHostDriver(HostBaseDriver):

    def __init__(self):
        LOG.info("initializing TerraHostDriver")
        self.client = TerraRestClient.create_client()

    def _call_client(self, method, *args, **kwargs):
        try:
            return method(*args, **kwargs)
        except Exception as e:
            LOG.exception("Failed to call method %s: %s"
                          % (method.func_name, e))
            raise e

    def get_host(self, host):
        _host = self._call_client(self.client.get_host_topology,
                                      host=host)
        return {
                "hostname": _host['name'],
                "mgmt_ip": _host['managementIpAddress'],
                "connections": _host['connections']
                }

    def delete_host(self, host):
        return self._call_client(self.client.delete_host,
                                 host=host)

    def create_host(self, host, mgmt_ip, connections):

        return self._call_client(self.client.create_host,
                                 host=host, mgmt_ip=mgmt_ip,
                                 connections=connections)
