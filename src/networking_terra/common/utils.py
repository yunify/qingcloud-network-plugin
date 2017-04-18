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
import functools
from oslo_log import log as logging

#from oslo_concurrency import lockutils
import json
import os
import pprint

LOG = logging.getLogger(__name__)


def is_primitive(obj):
    return obj is None or not hasattr(obj, "__dict__") \
           or type(obj) in [int, float, bool, str, dict, list]


def obj_to_dict(obj, depth=1):
    ret = {}
    for prop, value in vars(obj).iteritems():
        # LOG.debug("property: %s, value: %s type: %s" % (property, value, type(value)))
        if is_primitive(value) or depth >= 2:
            ret[prop] = value
        else:
            ret[prop] = obj_to_dict(value, depth + 1)
    return ret


def log_context(log=False):
    def wrapper(func):
        @functools.wraps(func)
        def f(self, context, *args, **kwargs):
            LOG.info("calling %s" % func.func_name)
            if args:
                arg_num = 0
                for arg in args:
                    arg_num = arg_num + 1
                    LOG.info("argument %s: %s" % (arg_num, arg))
            if kwargs:
                for key in kwargs.keys():
                    LOG.info("%s: %s" % (key, kwargs.get(key)))
            obj = obj_to_dict(context)
            if log:
                LOG.info("\n%s" % pprint.pformat(obj))
            return func(self, context, *args, **kwargs)

        return f

    return wrapper


def log_parameter(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        LOG.info("calling %s" % func.func_name)
        if args:
            arg_num = 0
            for arg in args:
                arg_num = arg_num + 1
                LOG.info("argument %s: %s" % (arg_num, arg))
        if kwargs:
            for key in kwargs.keys():
                LOG.info("%s: %s" % (key, kwargs.get(key)))
        return func(*args, **kwargs)

    return wrapper


def dict_compare(origin, current):
    origin_keys = set(origin.keys())
    current_keys = set(current.keys())
    intersect_keys = origin_keys.intersection(current_keys)
    added = origin_keys - current_keys
    removed = current_keys - origin_keys
    modified = {o: (origin[o], current[o]) for o in intersect_keys if origin[o] != current[o]}
    same = set(o for o in intersect_keys if origin[o] == current[o])
    LOG.info("same: %s" % same)
    LOG.info("removed: %s" % removed)
    LOG.info("modified: %s" % modified)
    LOG.info("added: %s" % added)
    return added, removed, modified, same


all_vlans = set(range(1050, 1200))
file_name = "/tmp/test.json"

def get_or_create_fake_local_vlan(network_id):
#     with lockutils.lock("vlan_mappine"):
        if not os.path.exists(file_name):
            f = open(file_name, "w+")
            vlan_mapping = {}
        else:
            f = open(file_name, "r+")
            s = f.read()
            vlan_mapping = json.loads(s)

        if vlan_mapping.has_key(network_id):
            f.close()
            LOG.info("read vlan: %s" % vlan_mapping[network_id])
            return vlan_mapping[network_id]

        f.seek(0)
        used_vlans = set(vlan_mapping.values())
        unused_vlans = all_vlans - used_vlans
        if len(unused_vlans):
            vlan = list(unused_vlans)[0]
            vlan_mapping[network_id] = vlan
            f.write(json.dumps(vlan_mapping))
            f.truncate()
            f.close()
            LOG.info("new vlan: %s" % vlan_mapping[network_id])
            return vlan
        else:
            f.close()
            raise Exception

def release_fake_local_vlan(network_id):
#     with lockutils.lock("vlan_mappine"):
        if not os.path.exists(file_name):
            f = open(file_name, "w+")
            vlan_mapping = {}
        else:
            f = open(file_name, "r+")
            s = f.read()
            vlan_mapping = json.loads(s)

        if vlan_mapping.has_key(network_id):
            f.seek(0)
            vlan = vlan_mapping.pop(network_id)
            f.write(json.dumps(vlan_mapping))
            f.truncate()
            LOG.info("release vlan: %s" % vlan)
            f.close()
