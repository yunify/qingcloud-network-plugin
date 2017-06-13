# Copyright (c) 2017 Tethrnet Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from neutron.callbacks.resources import ROUTER_INTERFACE
from oslo_config import cfg
from oslo_log import log as logging

from neutron.agent import securitygroups_rpc
from neutron_lib import constants
from neutron.extensions import portbindings
from neutron.plugins.ml2 import driver_api as api
from neutron.plugins.ml2.common import exceptions as ml2_exc

from networking_terra.common.client import TerraRestClient
from networking_terra.common.constants import supported_network_types
from networking_terra.common.utils import log_context
from networking_terra.common.utils import dict_compare
from networking_terra.common.exceptions import NotFoundException
from neutron.plugins.ml2.common.exceptions import MechanismDriverError

LOG = logging.getLogger(__name__)
cfg.CONF.import_group('ml2_terra', 'networking_terra.common.config')


class TerraMechanismDriver(api.MechanismDriver):
    def initialize(self):
        LOG.info("initializing TerraMechanismDriver")
        self.client = TerraRestClient.create_client()
        self._vif_details = {
            portbindings.CAP_PORT_FILTER: securitygroups_rpc.is_firewall_enabled(),
        }
        self.physical_network = cfg.CONF.ml2_terra.physical_network
        self.complete_binding = cfg.CONF.ml2_terra.complete_binding
        self.binding_level = cfg.CONF.ml2_terra.binding_level
        self.host_mapping = {}

#         self._init_sg_callbacks()
        LOG.info("TerraMechanismDriver initialized")

    @log_context()
    def check_vlan_transparency(self, context):
        return False

    def _get_vif_details(self, agent, port_binding, context):
        details = dict(self._vif_details)
        details[portbindings.VIF_DETAILS_VLAN] = port_binding['local_vlan']
        return details

    def _refresh_host_mapping(self):

        # host_mapping = {
        #     "ubuntu": [{
        #         "device_name": "switch1",
        #         "port_name": "GigaEthernet1/0/1"
        #     }],
        #     "compute2": [{
        #         "device_name": "switch2",
        #         "port_name": "GigaEthernet1/0/1"
        #     }]
        # }
        host_mapping = {}
        mapping = self._call_client(self.client.get_host_topology)
        if not mapping:
            LOG.error("failed to get hsot mapping from Terra dc controller")
            raise ml2_exc.MechanismDriverError()
        for host in mapping["vnetHostList"]:
            name = host["name"]
            host_mapping[name] = []
            for conn in host["connections"]:
                body = {
                    "device_name": conn["switchName"],
                    "port_name": conn["port"]
                }
                host_mapping[name].append(body)
        self.host_mapping = host_mapping

    def _call_client(self, method, *args, **kwargs):
        try:
            return method(*args, **kwargs)
        except Exception as e:
            LOG.error("Failed to call method %s: %s"
                      % (method.func_name, e))
            # ignore notfound when delete resource
            if not (method.func_name.startswith('delete') and
                    isinstance(e, NotFoundException)):
                LOG.exception(e)
                raise ml2_exc.MechanismDriverError(method=method)

    @log_context(False)
    def create_network_postcommit(self, context):
        if context.current['provider:network_type'] not in supported_network_types:
            LOG.warning("Terra driver currently only support vxlan type")
            return

        net_id = context.current['id']
        net_name = context.current['name']
        args = {
            'id': net_id,
            'tenant_id': context.current.get('tenant_id'),
            'name': net_name,
            'network_type': context.current['provider:network_type'],
            'external': context.current.get('router:external', False),
            'segment_id': context.current['provider:segmentation_id']}
        LOG.debug("create network: %s" % args)
        self._call_client(self.client.create_network, **args)

    @log_context()
    def update_network_postcommit(self, context):
        dict_compare(context.original, context.current)

    @log_context()
    def delete_network_postcommit(self, context):
        net_id = context.current['id']
        LOG.debug("delete network: %s" % net_id)
        self._call_client(self.client.delete_network, net_id)
        self._call_client(self.client.delete_vlan_domain, net_id)

    @log_context(True)
    def create_subnet_postcommit(self, context):
        subnet_id = context.current['id']
        subnet_name = context.current['name']
        args = {
            'id': subnet_id,
            'tenant_id': context.current['tenant_id'],
            'name': subnet_name,
            'network_id': context.current['network_id'],
            'gateway_ip': context.current['gateway_ip'],
            'enable_dhcp': context.current['enable_dhcp'],
            'cidr': context.current['cidr']
        }
        LOG.debug("create subnet: %s" % args)
        self._call_client(self.client.create_subnet, **args)

    @log_context()
    def update_subnet_postcommit(self, context):
        dict_compare(context.original, context.current)

    @log_context()
    def delete_subnet_postcommit(self, context):
        subnet_id = context.current['id']
        LOG.debug("delete subnet: %s" % subnet_id)
        self._call_client(self.client.delete_subnet, subnet_id)

    def _get_binding_level(self, context):
        if context._binding_levels:
            return context._binding_levels[-1].level + 1
        else:
            return 0

    @log_context(True)
    def bind_port(self, context):
        level = self._get_binding_level(context)
        if level != self.binding_level:
            LOG.info("Terra mech driver is working on level: %s, current level: %s" %
                     (self.binding_level, level))
            return
        agents = context.host_agents(constants.AGENT_TYPE_OVS)
        if not agents:
            LOG.warning("Port %(pid)s on network %(network)s not bound, "
                        "no agent registered on host %(host)s",
                        {'pid': context.current['id'],
                         'network': context.network.current['id'],
                         'host': context.host})
        for agent in agents:
            LOG.debug("Checking agent: %s", agent)
            for segment in context.segments_to_bind:
                if segment['network_type'] not in supported_network_types:
                    LOG.info("Terra mechanism driver don't support network_type: %s"
                             % segment['network_type'])
                    continue
                host = agent['host']
                self._refresh_host_mapping()

                # currently only bind to first port
                switch_ports = self.host_mapping.get(host, None)
                if not switch_ports:
                    LOG.error("Can't find host in switch mapping, can't bind port")
                    raise ml2_exc.MechanismDriverError()

                vlan_id = context._network_context.current['provider:vlan_id']
                vni = context._network_context.current[
                                                    'provider:segmentation_id']

                domain_id = self._get_domain_id(context.network.current['id'],
                                                vlan_id)

                try:
                    self._call_client(self.client.get_vlan_domain,
                                      id=domain_id)
                except MechanismDriverError:
                    LOG.info("vlan binding [%s] does not exist, create"
                             % context.current['id'])
                    args = {
                        # use the same id for domain and
                        # binding to delete it when unbind
                        'id': domain_id,
                        'name': domain_id,
                        'start_vlan': vlan_id,
                        'end_vlan': vlan_id,
                        'start_vxlan': vni,
                        'end_vxlan': vni,
                    }
                    LOG.debug("create vlan domain: %s" % args)
                    self._call_client(self.client.create_vlan_domain, **args)

                args = {
                    'id': context.current['id'],
                    'tenant_id': context.current.get('tenant_id'),
                    'vlan_domain_id': domain_id,
                    'bind_port_list': switch_ports,
                }

                native_vlan = context.current.get('native_vlan')
                if native_vlan:
                    args['untagged_vni'] = vni

                LOG.debug("bind port: %s" % args)
                self._call_client(self.client.create_port_binding, **args)

    def _get_domain_id(self, network_id, vlan_id):
        return "%s_%s" % (network_id, vlan_id)

    @log_context(True)
    def create_port_postcommit(self, context):
        port = context.current
        if port['device_id'] and port['device_owner'] == ROUTER_INTERFACE:
            # this is a router interface
            LOG.debug("adding a router port: %s" % port)

    @log_context()
    def update_port_postcommit(self, context):
        dict_compare(context.original, context.current)
        if context.original['device_id'] and not context.current['device_id']:
            port_id = context.current['id']
            LOG.debug("port device_id change to none, delete port binding: %s", port_id)
            # nova detach a neutron-created port
            self._call_client(self.client.delete_port_binding, port_id)

    @log_context(True)
    def delete_port_postcommit(self, context):
        if context.host and context.host != '':
            if context.current['device_id']:

                binding = None
                try:
                    binding = self._call_client(self.client.get_port_binding,
                                                context.current['id'])
                except MechanismDriverError:
                    LOG.info("port binding [%s] is not found"
                             % context.current['id'])
                    return

                LOG.debug("delete port: %s" % context.current['id'])
                self._call_client(self.client.delete_port_binding,
                                  context.current['id'])

                try:

                    if binding:
                        domain_id = binding["binding"]["vlan_domain_id"]
                        LOG.debug("delete vlan domain: %s" % domain_id)
                        self._call_client(self.client.delete_vlan_domain,
                                          domain_id)
                except MechanismDriverError:
                    # due to lacking of query api, delete it directly
                    # and ignore error if has dependence
                    pass

        else:
            LOG.info("port don't have binding")
