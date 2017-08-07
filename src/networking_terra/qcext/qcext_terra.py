from time import sleep
from networking_terra.common.exceptions import BadRequestException
from oslo_log import log as logging
from networking_terra.common.client import TerraRestClient
from common.qcext_api import QcExtBaseDriver
from networking_terra.common.exceptions import NotFoundException
from networking_terra.common.utils import call_client

LOG = logging.getLogger(__name__)


class TerraQcExtDriver(QcExtBaseDriver):
    def __init__(self):
        LOG.info("initializing TerraQcExtDriver")
        self.client = TerraRestClient.create_client()
        self._call_client = call_client

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

    def add_route(self, vpc_id, destination, nexthop, device_name):
        vpc_id = self.client.get_id_by_original_id("routers", vpc_id)
        switch = self.client.get_switch(device_name)
        payload = {
            "device_id": switch["id"],
            "destination": destination,
            "nexthop": nexthop,
        }
        url = self.client.url + "routers/%s/routes" % vpc_id
        self._call_client(self.client._post, url=url, payload=payload,
                          retry_badreq=10)

    def get_routes(self, vpc_id):
        try:
            _vpc_id = self.client.get_id_by_original_id("routers", vpc_id)
            url = self.client.url + "routers/%s/routes" % _vpc_id
            return self._call_client(self.client._get, url=url)
        except NotFoundException:
            LOG.info("no route in router [%s]" % vpc_id)
            return None

    def delete_routes(self, vpc_id, destination=None):
        '''
        @param vpc_id: vpc to delete routes
        @param destination: destination route to delete. None to delete all
        '''
        try:
            routes = self.get_routes(vpc_id)
            if not routes:
                return

            _vpc_id = self.client.get_id_by_original_id("routers", vpc_id)

            for route in routes:
                if not destination or route['destination'] == destination:
                    url = self.client.url + "routers/%s/routes/%s" \
                          % (_vpc_id, route['id'])
                    self._call_client(self.client._delete, url=url,
                                      retry_badreq=10)
        except NotFoundException:
            LOG.info("no route in router [%s]" % vpc_id)
            return None

    def create_direct_port(self, vxnet_id,
                           switch_name, interface_name,
                           ip_address, vlan_id, user_id):
        interface = self.client.get_switch_interface(switch_name,
                                                     interface_name)
        args = {"name": vxnet_id + "-subif",
                "tenant_id": user_id,
                "original_id": vxnet_id,
                "network_id": vxnet_id,
                "fixed_ips": [{"subnet_id": vxnet_id,
                               "ip_address": ip_address}],
                "switch_interface_id": interface['id'],
                "vlan_id": vlan_id}
        self.client.create_direct_port(**args)
