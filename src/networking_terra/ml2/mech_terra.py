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

from neutron_lib.constants import DEVICE_OWNER_ROUTER_INTF
from oslo_config import cfg
from oslo_log import log as logging

from neutron.agent import securitygroups_rpc
from neutron.extensions import portbindings
from neutron.plugins.ml2 import driver_api as api
from neutron.plugins.ml2.common import exceptions as ml2_exc

from networking_terra.common.client import TerraRestClient
from networking_terra.common.constants import *
from networking_terra.common.utils import log_context, call_client
from networking_terra.common.utils import dict_compare
from networking_terra.common.exceptions import NotFoundException,\
    BadRequestException

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
        self.l2_vni_pool = cfg.CONF.ml2_terra.l2_vni_pool_name
        self._call_client = call_client
        LOG.info("TerraMechanismDriver initialized")

    @log_context()
    def check_vlan_transparency(self, context):
        return False

    def get_host_switch_connection(self, host):
        mapping = self._call_client(self.client.get_host_links_by_hostname, host)
        if not mapping:
            LOG.error("failed to get host connection for [ %s ]" % host)
            raise ml2_exc.MechanismDriverError(method="get_host_switch_connection")
        link = mapping[0]
        switch_name = link["switch_name"]
        switch_interface_name = link["switch_interface_name"]
        return switch_name, switch_interface_name

    @log_context(True)
    def create_network_postcommit(self, context):
        if context.current['provider:network_type'] not in supported_network_types:
            LOG.warning("Terra driver don't support network type: %s" %
                        context.current['provider:network_type'] )
            return
        net_id = context.current['id']
        net_name = context.current['name']
        args = {
            'name': net_name,
            'original_id': net_id,
            'tenant_id': context.current['tenant_id'],
            'tenant_name': context._plugin_context.tenant_name,
            'segment_type': 'vxlan',
            'vni_pool_name': self.l2_vni_pool,
            "router_external": False
        }
        vni = context.current.get('provider:segmentation_id')
        if vni:
            args['segment_global_id'] = vni
        LOG.debug("create network: %s" % args)
        self._call_client(self.client.create_network, **args)

    @log_context()
    def update_network_postcommit(self, context):
        dict_compare(context.original, context.current)

    @log_context()
    def delete_network_postcommit(self, context):
        net_id = context.current['id']
        LOG.debug("delete network: %s" % net_id)
        try:
            self._call_client(self.client.delete_network, net_id)
        except NotFoundException:
            LOG.info("don't find network %s in fc" % net_id)
            return

    @log_context(True)
    def create_subnet_postcommit(self, context):
        subnet_id = context.current['id']
        subnet_name = context.current['name']
        args = {
            'name': subnet_name,
            'original_id': subnet_id,
            'tenant_id': context.current['tenant_id'],
            'tenant_name': context._plugin_context.tenant_name,
            'network_id': context.current['network_id'],
            'ip_version': 4,
            'cidr': context.current['cidr'],
            'gateway_ip': context.current['gateway_ip'],
            'enable_dhcp': context.current['enable_dhcp']
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
        try:
            self._call_client(self.client.delete_subnet, subnet_id)
        except NotFoundException:
            LOG.info("don't find subnet %s in fc" % subnet_id)
            return

    def _get_binding_level(self, context):
        if context._binding_levels:
            return context._binding_levels[-1].level + 1
        else:
            return 0

    def create_dynamic_segment(self, context, segment):
        session = context._plugin_context.session
        network_id = context._network_context.current['id']

        dynamic_segment = db.get_dynamic_segment(
            session, network_id, segment.get(api.PHYSICAL_NETWORK),
            segment.get(api.SEGMENTATION_ID))

        if dynamic_segment:
            return dynamic_segment

        db.add_network_segment(session, network_id, segment, is_dynamic=True)
        return segment

    def delete_dynamic_segment(self, context, segment):
        # currently don't delete, dynamic segment will be deleted when delete network
        pass

    @log_context(True)
    def bind_port(self, context):
        level = self._get_binding_level(context)
        if level != self.binding_level:
            LOG.info("Terra mech driver is working on level: %s, current level: %s" %
                     (self.binding_level, level))
            return
        network = context.network.current
        for segment in context.segments_to_bind:
            if segment['network_type'] not in supported_network_types:
                LOG.info("Terra driver don't support network_type: %s"
                         % segment['network_type'])
                continue
            host = context.host
            switch_name, interface_name = self.get_host_switch_connection(host)
            vlan_native = context.current.get('native_vlan')
            arg = {
                'network_id': network['id'],
                'switch_name': switch_name,
                'interface_name': interface_name,
                'vlan_native': vlan_native
            }
            if 'provider:vlan_id' in network:
                arg['local_vlan_id'] = network['provider:vlan_id']

            if vlan_native:
                # the port can not bind to different vlan in this mode
                try:
                    binding = self.client.get_port_binding(None, switch_name,
                                                           interface_name)
                    network_id = self.client.get_id_by_original_id(
                                                            "networks",
                                                            network['id'])
                    if binding['network_id'] == network_id:
                        LOG.info("port [%s] already has binding, done"
                                 % interface_name)
                        return
                    else:
                        raise BadRequestException(
                            msg="interface [%s] has binding to [%s],"
                            "can not binding again"
                            % (interface_name, binding['network_id']))

                except NotFoundException:
                    # not found is expected
                    pass

            self._call_client(self.client.create_port_binding,
                              retry_badreq=10, **arg)

    @log_context(True)
    def create_port_postcommit(self, context):
        port = context.current
        args = {
            'name': port['name'],
            'original_id': port['id'],
            'tenant_id': port['tenant_id'],
            'tenant_name': context._plugin_context.tenant_name,
            'network_id': port['network_id'],
            'fixed_ips': port['fixed_ips'],
        }
        LOG.debug("create port params: %s" % args)
        self._call_client(self.client.create_port, **args)
        # this is a router interface
        LOG.debug("adding a router port: %s" % port)

    def unbind_port(self, context):
        port_id = context.current['id']
        self._call_client(self.client.port_unbind, port_id)

    @log_context()
    def update_port_postcommit(self, context):
        dict_compare(context.original, context.current)
        if context.original['device_id'] and not context.current['device_id']:
            port_id = context.current['id']
            LOG.debug("port device_id change to none, delete port binding: %s", port_id)
            # nova detach a neutron-created port
            self.unbind_port(context)

    @log_context(True)
    def delete_port_postcommit(self, context):
        port = context.current
        if port['device_id'] and port['device_owner'] == DEVICE_OWNER_ROUTER_INTF:
            # in remove router interface by subnet case, do not delete port here,
            # port will be deleted in remove_router_interface
            LOG.debug("don't delete router interface here")
            return
        if context.host and context.current['device_id']:
            try:
                switch_name, interface_name = \
                    self.get_host_switch_connection(context.host)
                network_id = context.network.current['id']
                args = {
                    'network_id': network_id,
                    'switch_name': switch_name,
                    'interface_name': interface_name,
                }
                LOG.debug("delete_port_binding: %s" % args)
                self._call_client(self.client.delete_port_binding,
                                  retry_badreq=10, **args)
            except NotFoundException:
                LOG.info("port binding not found for host [%s] in net [%s]"
                         % (context.host, network_id))
                return
