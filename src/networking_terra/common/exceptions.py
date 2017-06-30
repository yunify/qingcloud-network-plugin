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

from neutron_lib import exceptions as exc


class RequestFailedError(exc.NeutronException):
    message = "%(msg)s"


class AuthenticationException(exc.NeutronException):
    message = "Authentication failed"


class TimeoutException(exc.NeutronException):
    message = "Request Timeout"


class BadRequestException(exc.NeutronException):
    message = "BadRequest: %(msg)s"


class NotFoundException(exc.NeutronException):
    message = "%(msg)s Not Found"


class ServerErrorException(exc.NeutronException):
    message = "Server Error: %(msg)s"

class HTTPErrorException(exc.NeutronException):
    message = "HTTP Error: %(msg)s"

class ClientException(exc.NeutronException):
    message = "Client Exception: %(msg)s"


class InitializException(exc.NeutronException):
    message = "%(msg)s"
