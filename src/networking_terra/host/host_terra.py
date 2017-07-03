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
        _host = self._call_client(self.client.get_host_by_name, host)
        if not _host:
            return None

        _links = self._call_client(self.client.get_host_links_by_hostname, host)
        _connections = []
        for link in _links:
            _connections.append({
                "host_name": link["host_name"],
                "host_interface_name": link["host_interface_name"],
                "switch_name": link["switch_name"],
                "switch_interface_name": link["switch_interface_name"]
            })

        return {
            "hostname": _host["hostname"],
            "mgmt_ip": _host["host_ip"],
            "connections": _connections
        }

    def delete_host(self, host):
        _host = self._call_client(self.client.get_host_by_name, host)
        _links = self._call_client(self.client.get_host_links_by_hostname, host)
        for link in _links:
            self._call_client(self.client.delete_host_link, link["id"])
        return self._call_client(self.client.delete_host, _host["id"])

    def create_host(self, host, mgmt_ip, connections):

        _host = self._call_client(self.client.create_host,
                                  hostname=host, mgmt_ip=mgmt_ip)
        _links = self._call_client(self.client.add_host_links, links=connections)
