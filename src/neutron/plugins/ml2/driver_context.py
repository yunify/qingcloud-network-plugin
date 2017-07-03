# Copyright (c) 2013 OpenStack Foundation
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

import copy

from neutron_lib import constants
from oslo_log import log

from neutron.plugins.ml2 import driver_api as api

LOG = log.getLogger(__name__)


class PortBinding(object):

    def __init__(self, **xargs):
        self.port_id = xargs.get('port_id')
        self.host = xargs.get('host')
        self.vnic_type = xargs.get('vnic_type')
        self.profile = xargs.get('profile')
        self.vif_type = xargs.get('vif_type')
        self.vif_details = xargs.get('vif_details')

class PluginContext():
    def __init__(self, tenant_name):
        self._tenant_name = tenant_name

    @property
    def tenant_name(self):
        return self._tenant_name

class NetworkContext(api.NetworkContext):

    def __init__(self, network,
                 original_network=None, plugin_context=None):
        self._plugin_context = plugin_context
        self._network = network
        self._original_network = original_network

    @property
    def current(self):
        return self._network

    @property
    def original(self):
        return self._original_network

    @property
    def network_segments(self):
        return None


class SubnetContext(api.SubnetContext):

    def __init__(self, subnet, network,
                 original_subnet=None, plugin_context=None):
        self._subnet = subnet
        self._original_subnet = original_subnet
        self._network_context = NetworkContext(network) if network else None
        self._plugin_context = plugin_context

    @property
    def current(self):
        return self._subnet

    @property
    def original(self):
        return self._original_subnet

    @property
    def network(self):
        return self._network_context


class PortContext(api.PortContext):

    def __init__(self, port, network, binding, plugin_context=None):
        self._port = port
        self._original_port = None
        self._network_context = NetworkContext(network) if network else None
        self._plugin_context = plugin_context

        self._binding = copy.deepcopy(binding)
        self._binding_levels = 0

        # get segment from network
        self._segments_to_bind = None
        if 'provider:network_type' in self._network_context.current:
            self._segments_to_bind = [
                {'network_type':
                    self._network_context.current['provider:network_type'],
                 'id':
                    self._network_context.current['provider:segmentation_id']}]

        self._new_bound_segment = None
        self._next_segments_to_bind = None

        self._original_vif_type = None
        self._original_vif_details = None
        self._original_binding_levels = None
        self._new_port_status = None

    # The following methods are for use by the ML2 plugin and are not
    # part of the driver API.

    def _prepare_to_bind(self, segments_to_bind):
        self._segments_to_bind = segments_to_bind
        self._new_bound_segment = None
        self._next_segments_to_bind = None

    def _clear_binding_levels(self):
        self._binding_levels = []

    def _push_binding_level(self, binding_level):
        self._binding_levels.append(binding_level)

    def _pop_binding_level(self):
        return self._binding_levels.pop()

    # The following implement the abstract methods and properties of
    # the driver API.

    @property
    def current(self):
        return self._port

    @property
    def original(self):
        return self._original_port

    @property
    def status(self):
        return None

    @property
    def original_status(self):
        return None

    @property
    def network(self):
        if not self._network_context:
            network = self._plugin.get_network(
                self._plugin_context, self.current['network_id'])
            self._network_context = NetworkContext(
                self._plugin, self._plugin_context, network)
        return self._network_context

    @property
    def binding_levels(self):
        if self._binding_levels:
            return [{
                api.BOUND_DRIVER: level.driver,
                api.BOUND_SEGMENT: self._expand_segment(level.segment_id)
            } for level in self._binding_levels]

    @property
    def original_binding_levels(self):
        if self._original_binding_levels:
            return [{
                api.BOUND_DRIVER: level.driver,
                api.BOUND_SEGMENT: self._expand_segment(level.segment_id)
            } for level in self._original_binding_levels]

    @property
    def top_bound_segment(self):
        if self._binding_levels:
            return self._expand_segment(self._binding_levels[0].segment_id)

    @property
    def original_top_bound_segment(self):
        if self._original_binding_levels:
            return self._expand_segment(
                self._original_binding_levels[0].segment_id)

    @property
    def bottom_bound_segment(self):
        if self._binding_levels:
            return self._expand_segment(self._binding_levels[-1].segment_id)

    @property
    def original_bottom_bound_segment(self):
        if self._original_binding_levels:
            return self._expand_segment(
                self._original_binding_levels[-1].segment_id)

    def _expand_segment(self, segment_id):
        pass

    @property
    def host(self):
        return self._binding.host

    @property
    def original_host(self):
        pass

    @property
    def vif_type(self):
        return self._binding.vif_type

    @property
    def original_vif_type(self):
        return self._original_vif_type

    @property
    def vif_details(self):
        return self._plugin._get_vif_details(self._binding)

    @property
    def original_vif_details(self):
        return self._original_vif_details

    @property
    def segments_to_bind(self):
        return self._segments_to_bind

    def host_agents(self, agent_type):
        return [{'host': self._binding.host}]

    def set_binding(self, segment_id, vif_type, vif_details,
                    status=None):
        pass

    def continue_binding(self, segment_id, next_segments_to_bind):
        pass

    def allocate_dynamic_segment(self, segment):
        pass

    def release_dynamic_segment(self, segment_id):
        pass
