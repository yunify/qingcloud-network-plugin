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

from networking_terra.common.utils import log_parameter


@log_parameter
def create_security_group(resource, event, trigger, **kwargs):
    pass


@log_parameter
def update_security_group(resource, event, trigger, **kwargs):
    pass


@log_parameter
def delete_security_group(resource, event, trigger, **kwargs):
    pass


@log_parameter
def validate_security_group_rule(resource, event, trigger, **kwargs):
    pass


@log_parameter
def create_security_group_rule(resource, event, trigger, **kwargs):
    pass


@log_parameter
def delete_security_group_rule(resource, event, trigger, **kwargs):
    pass
