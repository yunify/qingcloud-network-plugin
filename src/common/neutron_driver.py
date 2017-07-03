# =========================================================================
# Copyright 2012-present Yunify, Inc.
# -------------------------------------------------------------------------
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this work except in compliance with the License.
# You may obtain a copy of the License in the LICENSE file, or at:
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========================================================================

from oslo_config import cfg
from neutron.plugins.ml2.driver_context import PluginContext, NetworkContext, SubnetContext, \
    PortContext, PortBinding
from neutron.callbacks.resources import ROUTER_INTERFACE
from oslo_utils.importutils import import_class
from networking_terra.common.exceptions import ServerErrorException
from oslo_log import log as logging

NETWORK_TYPE_VXLAN = 'vxlan'
NETWORK_TYPE_SUBINTERFACE = 'local'
LOG = logging.getLogger(__name__)


def get_driver(ml2_name, l3_name, qcext_name, client_name, config_file):
    # load settings
    cfg.CONF(["--config-file", config_file])
    cfg.CONF.import_group("ml2_terra", "networking_terra.common.config")

    LOG.info("loaded config_file [%s]",
             config_file)
    LOG.info("loaded url [%s]",
             cfg.CONF.ml2_terra.url)

    ml2 = import_class(ml2_name)()
    l3 = import_class(l3_name)()
    qcext = import_class(qcext_name)()

    ml2.initialize()

    return NeutronDriver(l3, ml2, qcext)


class L3Context(object):
    def __init__(self, attrs):
        for key in attrs:
            self.__dict__[key] = attrs[key]

    def get(self, key):
        return self.__dict__.get(key)

    def __getitem__(self, key):
        return self.__dict__[key]

    def __iter__(self):
        return self.__dict__.__iter__()

    def __str__(self):
        return str(self.__dict__)


class NeutronDriver(object):
    def __init__(self, l3, ml2, qcext):
        self.l3 = l3
        self.ml2 = ml2
        self.qcext = qcext

    def create_vpc(self, vpc_id, l3vni, user_id, bgp_peers=None):
        '''
        vpc is a VRF with l3vni used by evpn
        '''
        router = {"tenant": user_id,
                  "tenant_name": user_id,
                  "id": vpc_id,
                  "name": vpc_id,
                  'l3_vni': l3vni}

        router_context = L3Context(router)

        self.l3.create_router(router_context, vpc_id)

        if bgp_peers:
            for bgp_peer in bgp_peers:
                as_number = bgp_peer.as_number
                device_name = bgp_peer.device_name
                ip_address = bgp_peer.ip_address
                self.qcext.add_router_bgp_peer(vpc_id, as_number,
                                               ip_address, device_name)

    def delete_vpc(self, vpc_id, user_id):

        router_context = L3Context({"tenant": user_id,
                                    "id": vpc_id})
        self.qcext.delete_router_bgp_peers(vpc_id)

        self.l3.delete_router(router_context, vpc_id)

    def create_vxnet(self, vxnet_id, vni, ip_network, gateway_ip, user_id,
                     network_type=NETWORK_TYPE_VXLAN, enable_dhcp=False):
        '''
        vxnet is a network with only one subnet
        '''

        network = {"tenant_id": user_id,
                   "id": vxnet_id,
                   "name": vxnet_id,
                   'provider:network_type': network_type}
        # for subinterface case, network type is "local" and don't specify vni
        if vni:
            network['provider:segmentation_id'] = vni

        network_context = NetworkContext(network,
                                         plugin_context=PluginContext(user_id))

        self.ml2.create_network_precommit(network_context)
        self.ml2.create_network_postcommit(network_context)

        subnet_id = vxnet_id
        subnet = {"tenant_id": user_id,
                  "id": subnet_id,
                  "name": subnet_id,
                  'network_id': vxnet_id,
                  'gateway_ip': gateway_ip,
                  'cidr': ip_network,
                  'enable_dhcp': enable_dhcp}

        subnet_context = SubnetContext(subnet, network,
                                       plugin_context=PluginContext(user_id))
        self.ml2.create_subnet_precommit(subnet_context)
        self.ml2.create_subnet_postcommit(subnet_context)

    def delete_vxnet(self, vxnet_id, user_id):

        network = {"tenant_id": user_id,
                   "id": vxnet_id,
                   "name": vxnet_id}

        network_context = NetworkContext(network)

        subnet_id = vxnet_id
        subnet = {"tenant_id": user_id,
                  "id": subnet_id,
                  "name": subnet_id,
                  'network_id': vxnet_id}

        subnet_context = SubnetContext(subnet, network)

        self.ml2.delete_subnet_precommit(subnet_context)
        self.ml2.delete_subnet_postcommit(subnet_context)

        self.ml2.delete_network_precommit(network_context)
        self.ml2.delete_network_postcommit(network_context)

    def join_vpc(self, vpc_id, subnet_id, user_id):
        '''
        add network to VRF
        '''
        interface_context = L3Context({'subnet_id': subnet_id})

        self.l3.add_router_interface(interface_context, vpc_id,
                                     None)

    def leave_vpc(self, vpc_id, vxnet_id, user_id):

        interface_context = L3Context({'subnet_id': vxnet_id})

        self.l3.remove_router_interface(interface_context, vpc_id,
                                        None)

    def add_subintf(self, vpc_id, network_id, ip_address,
                    switch_name, interface_name, vlan_id, user_id):

        self.qcext.create_direct_port(network_id,
                                      switch_name, interface_name,
                                      ip_address, vlan_id, user_id)
        port_id = network_id
        interface_info = {"port_id": port_id,
                          "subnet_id": network_id}
        self.l3.add_router_interface(L3Context(interface_info), vpc_id,
                                     interface_info)

    def delete_subintf(self, vpc_id, network_id):
        interface_info = {"port_id": network_id,
                          "subnet_id": network_id}
        # port will be delete when remove router interface
        self.l3.remove_router_interface(L3Context(interface_info), vpc_id,
                                        interface_info)

    def add_node(self, vxnet_id, vni, host, user_id, vlan_id,
                 native_vlan=True):
        '''
        @param native_vlan: True, for baremetal
                            False, for hypervisor
        '''

        network = {"tenant_id": user_id,
                   "id": vxnet_id,
                   "name": vxnet_id,
                   'provider:segmentation_id': vni,
                   'provider:network_type': NETWORK_TYPE_VXLAN,
                   'provider:vlan_id': vlan_id}

        port = {"tenant_id": user_id,
                "id": self._get_port_id(vxnet_id, host),
                'network_id': vxnet_id,
                'device_owner': ROUTER_INTERFACE,
                'device_id': vxnet_id,
                'native_vlan': native_vlan}

        binding = PortBinding(host=host)

        port_context = PortContext(port, network, binding,
                                   plugin_context=PluginContext(user_id))
        self.ml2.bind_port(port_context)

    def remove_node(self, vxnet_id, host, user_id):

        network = {"tenant_id": user_id,
                   "id": vxnet_id,
                   "name": vxnet_id}

        port = {"tenant_id": user_id,
                "id": self._get_port_id(vxnet_id, host),
                'network_id': vxnet_id,
                'device_owner': ROUTER_INTERFACE,
                'device_id': vxnet_id}
        binding = PortBinding(host=host)
        port_context = PortContext(port, network, binding)

        self.ml2.delete_port_precommit(port_context)
        self.ml2.delete_port_postcommit(port_context)

    def _get_port_id(self, vxnet_id, host):
        return "%s_%s" % (vxnet_id, host)

    def create_host(self, hostname, mgmt_ip, connections):
        return self.qcext.create_host(hostname, mgmt_ip,
                                            connections)

    def get_host(self, hostname):

        try:
            return self.qcext.get_host(hostname)
        # TODO server should return NotFoundException
        except ServerErrorException:
            pass

        return None

    def delete_host(self, hostname):
        return self.qcext.delete_host(hostname)


class BgpPeer(object):
    def __init__(self, ip_address, as_number, device_name,
                 advertise_host_route=False):
        self.ip_address = ip_address
        self.as_number = as_number
        self.device_name = device_name
        self.advertise_host_route = advertise_host_route

    def to_dict(self):
        return {
            'ip_address': self.ip_address,
            'as_number': self.as_number,
            'device_name': self.device_name,
            'advertise_host_route': self.advertise_host_route
        }
