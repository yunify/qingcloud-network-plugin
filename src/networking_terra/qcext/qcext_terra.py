from time import sleep
from networking_terra.common.exceptions import BadRequestException
from oslo_log import log as logging
from networking_terra.common.client import TerraRestClient
from common.qcext_api import QcExtBaseDriver
from networking_terra.common.exceptions import NotFoundException

LOG = logging.getLogger(__name__)


class TerraQcExtDriver(QcExtBaseDriver):
    def __init__(self):
        LOG.info("initializing TerraQcExtDriver")
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

    def add_router_bgp_peer(self, vpc_id, as_number, ip_address,
                            device_name):
        vpc_id = self.client.get_id_by_original_id("routers", vpc_id)
        switch = self.client.get_switch(device_name)
        payload = {
            "device_id": switch["id"],
            "as_number": as_number,
            "ip_address": ip_address,
            "advertise_host_route": False
        }
        try:
            return self.client._post(self.client.url +
                                     "routers/%s/bgp_neighbors" % vpc_id,
                                     payload)
        except BadRequestException:
            # failed in vpc consistent checking to avoid error from
            # cisco. Try again later
            sleep(60)
            return self.client._post(self.client.url +
                                     "routers/%s/bgp_neighbors" % vpc_id,
                                     payload)

    def delete_router_bgp_peers(self, vpc_id):
        bgp_peers = None
        try:
            bgp_peers = self.client.get_router_bgp_peers(vpc_id)
        except NotFoundException:
            return

        if not bgp_peers:
            return

        for peer in bgp_peers:
            try:
                self.client.delete_router_bgp_peer(vpc_id, peer['id'])
            except BadRequestException:
                # failed in vpc consistent checking to avoid error from
                # cisco. Try again later
                sleep(60)
                self.client.delete_router_bgp_peer(vpc_id, peer['id'])

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
