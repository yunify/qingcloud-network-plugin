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

from neutron.plugins.ml2.driver_context import NetworkContext, SubnetContext,\
                                               PortContext, PortBinding
from neutron.callbacks.resources import ROUTER_INTERFACE
from oslo_config import cfg
from oslo_utils.importutils import import_class


def get_driver(ml2_name, l3_name, config_file):

    # load settings
    cfg.CONF(["--config-file", config_file])

    ml2 = import_class(ml2_name)()
    l3 = import_class(l3_name)()

    ml2.initialize()

    return NeutronDriver(l3, ml2)


class L3Context(object):

    def __init__(self, attrs):
        self.context = attrs

    def __getitem__(self, key):
        return self.context[key]


class NeutronDriver(object):

    def __init__(self, l3, ml2):
        self.l3 = l3
        self.ml2 = ml2

    def create_vpc(self, vpc_id, l3vni, user_id):
        '''
        vpc is a VRF with l3vni used by evpn
        '''
        router_context = L3Context({"tenant_id": user_id,
                                    "id": vpc_id,
                                    "name": vpc_id,
                                    'segment_id': l3vni,
                                    'aggregate_cidrs': ""})

        self.l3.create_router(router_context, vpc_id)

    def delete_vpc(self, vpc_id, user_id):

        router_context = L3Context({"tenant_id": user_id,
                                    "id": vpc_id})

        self.l3.delete_router(router_context, vpc_id)

    def create_vxnet(self, vxnet_id, vni, ip_network, gateway_ip, user_id):
        '''
        vxnet is a network with only one subnet
        '''

        network = {"tenant_id": user_id,
                   "id": vxnet_id,
                   "name": vxnet_id,
                   'provider:segmentation_id': vni,
                   'provider:network_type': 'vxlan'}

        network_context = NetworkContext(network)

#         subnet_id = "subnet-%s" % vxnet_id
        subnet_id = vxnet_id
        subnet = {"tenant_id": user_id,
                  "id": subnet_id,
                  "name": subnet_id,
                  'network_id': vxnet_id,
                  'gateway_ip': gateway_ip,
                  'cidr': ip_network,
                  'enable_dhcp': False}

        subnet_context = SubnetContext(subnet, network)

        self.ml2.create_network_precommit(network_context)
        self.ml2.create_network_postcommit(network_context)

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

    def join_vpc(self, vpc_id, vxnet_id, user_id):
        '''
        add network to VRF
        '''
        interface_context = L3Context({'subnet_id': vxnet_id})

        self.l3.add_router_interface(interface_context, vpc_id,
                                     None)

    def leave_vpc(self, vpc_id, vxnet_id, user_id):

        interface_context = L3Context({'subnet_id': vxnet_id})

        self.l3.remove_router_interface(interface_context, vpc_id,
                                        None)

    def add_node(self, vxnet_id, vni, host, user_id, native_vlan=True):
        '''
        @param native_vlan: True, for baremetal
                            False, for hypervisor
        '''

        network = {"tenant_id": user_id,
                   "id": vxnet_id,
                   "name": vxnet_id,
                   'provider:segmentation_id': vni,
                   'provider:network_type': 'vxlan'}

        port = {"tenant_id": user_id,
                "id": self._get_port_id(vxnet_id, host),
                'network_id': vxnet_id,
                'device_owner': ROUTER_INTERFACE,
                'device_id': vxnet_id,
                'native_vlan': native_vlan}

        binding = PortBinding(host=host)

        port_context = PortContext(port, network, binding)
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
