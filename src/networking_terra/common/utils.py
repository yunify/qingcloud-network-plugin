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
from networking_terra.common.exceptions import BadRequestException
from time import sleep

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


def call_client(method, *args, **kwargs):

    retry_badreq = kwargs.get("retry_badreq", None)
    if retry_badreq is not None:
        del kwargs["retry_badreq"]
    else:
        retry_badreq = 0

    while True:
        ret = None
        try:
            ret = method(*args, **kwargs)
        except BadRequestException as e:
            if retry_badreq <= 0:
                raise e
            retry_badreq -= 1
            sleep(60)
            continue
        except Exception as e:
            LOG.exception("Failed to call method %s: %s"
                          % (method.func_name, e))
            raise e
        return ret
