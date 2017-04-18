from neutron.plugins.ml2.driver_context import NetworkContext, SubnetContext,\
                                               PortContext, PortBinding
from neutron.callbacks.resources import ROUTER_INTERFACE


class L3Context(object):

    def __init__(self, attrs):
        self.context = attrs

    def __getitem__(self, key):
        return self.context[key]


class NeutronDriver(object):

    def __init__(self, l3, ml2):
        self.l3 = l3
        self.ml2 = ml2

    def create_vpc(self, router_id, l3vni, user_id):
        '''
        vpc is a VRF with l3vni used by evpn
        '''
        router_context = L3Context({"tenant_id": user_id,
                                    "id": router_id,
                                    "name": str(l3vni),
                                    'segment_id': l3vni,
                                    'aggregate_cidrs': ""})

        self.l3.create_router(router_context, router_id)

    def delete_vpc(self, router_id, l3vni, user_id):

        router_context = L3Context({"tenant_id": user_id,
                                    "id": router_id})

        self.l3.delete_router(router_context, router_id)

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

    def join_vpc(self, router_id, vxnet_id, user_id):
        '''
        add network to VRF
        '''
        interface_context = L3Context({'subnet_id': vxnet_id})

        self.l3.add_router_interface(interface_context, router_id,
                                     None)

    def leave_vpc(self, router_id, vxnet_id, user_id):

        interface_context = L3Context({'subnet_id': vxnet_id})

        self.l3.remove_router_interface(interface_context, router_id,
                                        None)

    def add_node(self, vxnet_id, vni, host, user_id):

        network = {"tenant_id": user_id,
                   "id": vxnet_id,
                   "name": vxnet_id,
                   'provider:segmentation_id': vni,
                   'provider:network_type': 'vxlan'}

        port = {"tenant_id": user_id,
                "id": vxnet_id,
                'network_id': vxnet_id,
                'device_owner': ROUTER_INTERFACE,
                'device_id': vxnet_id}
        binding = PortBinding(host=host)

        port_context = PortContext(port, network, binding)
        self.ml2.bind_port(port_context)

    def remove_node(self, vxnet_id, host, user_id):

        network = {"tenant_id": user_id,
                   "id": vxnet_id,
                   "name": vxnet_id}

        port = {"tenant_id": user_id,
                "id": vxnet_id,
                'network_id': vxnet_id,
                'device_owner': ROUTER_INTERFACE,
                'device_id': vxnet_id}
        binding = PortBinding(host=host)
        port_context = PortContext(port, network, binding)

        self.ml2.delete_port_precommit(port_context)
        self.ml2.delete_port_postcommit(port_context)
