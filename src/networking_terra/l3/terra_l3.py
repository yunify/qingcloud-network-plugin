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
from oslo_log import log as logging
from networking_terra.common.client import TerraRestClient
from networking_terra.common.exceptions import NotFoundException
from networking_terra.common.utils import log_context
from neutron.extensions.l3 import RouterPluginBase
from oslo_config import cfg
import traceback

LOG = logging.getLogger(__name__)
cfg.CONF.import_group("ml2_terra", "networking_terra.common.config")


class TerraL3RouterPlugin(RouterPluginBase):

    def __init__(self):
        LOG.info("initializing Terra L3 driver")
        super(TerraL3RouterPlugin, self).__init__()
        self.client = TerraRestClient.create_client()
        self.l3_vni_pool = cfg.CONF.ml2_terra.l3_vni_pool_name
        LOG.info("Terra L3 driver initialized")

    def _call_client(self, method, *args, **kwargs):
        try:
            method(*args, **kwargs)
        except Exception as e:
            LOG.error("Failed to call method %s: %s"
                      % (method.func_name, e))
            LOG.error(traceback.format_exc())
            raise e

    @log_context(True)
    def create_router(self, context, router):
        router_dict = super(TerraL3RouterPlugin, self).create_router(
            context, router)

        LOG.debug("created router_db: %s" % router_dict)
        kwargs = {
            'name': router_dict['name'],
            'tenant_id': context.tenant,
            'tenant_name': context.tenant_name,
            'original_id': router_dict['id'],
            'l3_vni': router_dict['l3_vni'],
            'vni_pool_name': self.l3_vni_pool
        }
        LOG.debug("create router: %s" % kwargs)

        try:
            self._call_client(self.client.create_router, **kwargs)
        except Exception as e:
            LOG.error("Failed to create router in terra dc controller: %s" % e.msg)
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
            LOG.info("don't find router %s in fc" % id)
            return

    @log_context(True)
    def add_router_interface(self, context, router_id, interface_info):
        router_interface_info = super(TerraL3RouterPlugin, self).add_router_interface(
            context, router_id, interface_info)
        subnet_id = router_interface_info.get('subnet_id')
        port_id = router_interface_info.get('port_id')

        LOG.debug("add router interface: router_id: %s, subnet_id: %s, port_id: %s"
                  % (router_id, subnet_id, port_id))
        self._call_client(self.client.add_router_interface,
                          router_id, subnet_id, port_id)

        return router_interface_info

    @log_context(True)
    def remove_router_interface(self, context, router_id, interface_info):
        router_interface_info = super(TerraL3RouterPlugin, self).remove_router_interface(
            context, router_id, interface_info)
        subnet_id = router_interface_info.get('subnet_id')
        port_id = router_interface_info.get('port_id')
        LOG.debug("remove router interface: router_id: %s, subnet_id: %s" %
                  (router_id, subnet_id))
        try:
            self._call_client(self.client.del_router_interface,
                              router_id, subnet_id, port_id)
        except NotFoundException as e:
            LOG.info("don't find router %s or subnet %s in fc" % (router_id, subnet_id))

        if port_id:
            try:
                self._call_client(self.client.delete_port, port_id)
            except NotFoundException as e:
                LOG.info("don't find port %s in fc" % port_id)
            return router_interface_info
