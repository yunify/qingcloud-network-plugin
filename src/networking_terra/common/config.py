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

from oslo_config import cfg


odl_opts = [
    cfg.StrOpt('url',
               help="HTTP URL of terra dc controller REST interface."),
    cfg.StrOpt('auth_url',
               help="HTTP Authentication URL of terra dc controller."),
    cfg.StrOpt('username',
               help="HTTP username for authentication."),
    cfg.StrOpt('password',
               secret=True,
               help="HTTP password for authentication."),
    cfg.IntOpt('http_timeout',
               default=10,
               help="HTTP timeout in seconds."),
    cfg.StrOpt('physical_network',
               help="physical network used for ovs vlan type."),
    cfg.BoolOpt('complete_binding',
                default=False,
                help="Whether Terra driver should complete port binding."),
    cfg.IntOpt('binding_level',
               default=0,
               help="Port binding level that Terra mech driver work on."),
    cfg.IntOpt('restconf_poll_interval',
               default=30,
               help="Poll interval in seconds for getting ODL hostconfig"),
    cfg.IntOpt('report_interval',
               default=10,
               help="report interval for topology discovery agent"),
    cfg.StrOpt('origin_name',
               default='qingcloud',
               help="Origin name that terra dc controller will use."),
]

cfg.CONF.register_opts(odl_opts, "ml2_terra")


def list_opts():
    return [('ml2_terra', odl_opts)]
