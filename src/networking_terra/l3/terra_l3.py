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
# from oslo_utils import excutils
from oslo_log import log as logging
from networking_terra.common.client import TerraRestClient
from networking_terra.common.utils import log_context
from neutron.extensions.l3 import RouterPluginBase
from networking_terra.common.exceptions import NotFoundException

LOG = logging.getLogger(__name__)


class TerraL3RouterPlugin(RouterPluginBase):

    def __init__(self):
        LOG.info("initializing Terra L3 driver")
        super(TerraL3RouterPlugin, self).__init__()
        self.client = TerraRestClient.create_client()
        LOG.info("Terra L3 driver initialized")

    def _call_client(self, method, *args, **kwargs):
        try:
            method(*args, **kwargs)
        except Exception as e:
            LOG.error("Failed to call method %s: %s"
                      % (method.func_name, e.message))
            raise e

    @log_context(True)
    def create_router(self, context, router):
        router_dict = super(TerraL3RouterPlugin, self).create_router(
            context, router)

        aggregate_cidrs = []
        LOG.debug("created router_db: %s" % router_dict)
        kwargs = {
            'id': router_dict['id'],
            'tenant_id': router_dict['tenant_id'],
            'name': router_dict['name'],
            'segment_id': router_dict['segment_id'],
            'ecmp_number': 3,
            'aggregate_cidrs': aggregate_cidrs
        }
        LOG.debug("create router: %s" % kwargs)

        try:
            self._call_client(self.client.create_router, **kwargs)
        except Exception as e:
            LOG.error("Failed to create router in terra dc controller: %s" % e.message)
            router_dict = super(TerraL3RouterPlugin, self).delete_router(
                context, router_dict['id'])
            raise e

        return router_dict

    @log_context(True)
    def delete_router(self, context, id):
        super(TerraL3RouterPlugin, self).delete_router(context, id)

        LOG.debug("delete router: %s" % id)
        try:
            self._call_client(self.client.delete_router, id)
        except NotFoundException:
            # no found is OK for deletion
            LOG.info("router: %s can not be found" % id)
            pass

    @log_context(True)
    def add_router_interface(self, context, router_id, interface_info):
        router_interface_info = super(TerraL3RouterPlugin, self).add_router_interface(
            context, router_id, interface_info)

        LOG.debug("db created router interface: %s" % router_interface_info)
        subnet_id = router_interface_info['subnet_id']
        LOG.debug("add router interface: router_id: %s, subnet_id: %s" % (router_id, subnet_id))

        try:
            self._call_client(self.client.add_router_interface, router_id, subnet_id)
        except Exception as e:
            LOG.error("Failed to add router interface: %s", e.message)
            #outer_interface_info = super(TerraL3RouterPlugin, self).remove_router_interface(
            #    context, router_id, interface_info)
            raise e

        return router_interface_info

    @log_context(True)
    def remove_router_interface(self, context, router_id, interface_info):
        router_interface_info = super(TerraL3RouterPlugin, self).remove_router_interface(
            context, router_id, interface_info)

        subnet_id = router_interface_info['subnet_id']
        LOG.debug("remove router interface: router_id: %s, subnet_id: %s"
                  % (router_id, subnet_id))
        try:
            self._call_client(self.client.del_router_interface, router_id,
                              subnet_id)
        except NotFoundException:
            # no found is OK for deletion
            LOG.info("router: [%s], subnet_id: [%s] can not be found"
                     % (id, subnet_id))
            pass

        return router_interface_info
