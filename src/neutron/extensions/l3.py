# Copyright 2012 VMware, Inc.
# All rights reserved.
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

import abc
import six

from neutron._i18n import _


@six.add_metaclass(abc.ABCMeta)
class RouterPluginBase(object):

    @abc.abstractmethod
    def create_router(self, context, router):
        return context

    def update_router(self, context, id, router):
        pass

    def get_router(self, context, id, fields=None):
        pass

    @abc.abstractmethod
    def delete_router(self, context, id):
        return context

    def get_routers(self, context, filters=None, fields=None,
                    sorts=None, limit=None, marker=None, page_reverse=False):
        pass

    @abc.abstractmethod
    def add_router_interface(self, context, router_id, interface_info=None):
        return context

    @abc.abstractmethod
    def remove_router_interface(self, context, router_id, interface_info):
        return context

    def create_floatingip(self, context, floatingip):
        pass

    def update_floatingip(self, context, id, floatingip):
        pass

    def get_floatingip(self, context, id, fields=None):
        pass

    def delete_floatingip(self, context, id):
        pass

    def get_floatingips(self, context, filters=None, fields=None,
                        sorts=None, limit=None, marker=None,
                        page_reverse=False):
        pass

    def get_routers_count(self, context, filters=None):
        raise NotImplementedError()

    def get_floatingips_count(self, context, filters=None):
        raise NotImplementedError()
