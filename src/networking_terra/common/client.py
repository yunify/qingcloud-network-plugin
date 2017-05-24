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
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils
import json
import requests
from requests import exceptions as r_exec

from networking_terra.common.exceptions import RequestFailedError, AuthenticationException, InitializException, \
    TimeoutException, ClientException, ServerErrorException, BadRequestException, NotFoundException

import pprint

LOG = logging.getLogger(__name__)
cfg.CONF.import_group("ml2_terra", "networking_terra.common.config")


class TerraRestClient(object):
    @classmethod
    def create_client(cls):
        if not cfg.CONF.ml2_terra.url:
            raise InitializException(msg="Terra dc url must be configured")
        if not cfg.CONF.ml2_terra.auth_url:
            raise InitializException(msg="Terra dc auth_url must be configured")
        if not cfg.CONF.ml2_terra.username:
            raise InitializException(msg="Terra dc username must be configured")
        if not cfg.CONF.ml2_terra.password:
            raise InitializException(msg="Terra dc password must be configured")

        return cls(
            cfg.CONF.ml2_terra.url,
            cfg.CONF.ml2_terra.auth_url,
            cfg.CONF.ml2_terra.username,
            cfg.CONF.ml2_terra.password,
            cfg.CONF.ml2_terra.http_timeout)

    def __init__(self, url, auth_url, username, password, timeout):
        if url.endswith("/"):
            self.url = url
        else:
            self.url = url + "/"
        self.auth_url = auth_url
        self.username = username
        self.password = password
        self.timeout = timeout
        self.token = None
        self.timeout_retry = 1
        self.token_retry = 1

    def _process_request(self, headers, method, url, payload_json, timeout=None):
            LOG.debug("_process_request: %(method)s %(url)s %(header)s %(body)s",
                      {"method": method,
                       "url": url,
                       "header": headers,
                       "body": payload_json})

            timeout_retry = self.timeout_retry + 1
            while timeout_retry:
                try:
                    if not timeout:
                        timeout = self.timeout
                    resp = requests.request(method, url, data=payload_json,
                                            headers=headers, timeout=timeout)
                    LOG.debug("Got response: %s, %s" % (resp.status_code, resp.text))
                    return resp
                except (r_exec.ConnectTimeout, r_exec.Timeout, r_exec.ReadTimeout, r_exec.ConnectionError) as e:
                    if timeout_retry > 1:
                        LOG.warn("Request timeout, retry: %s" % e)
                        timeout_retry -= 1
                        continue
                    else:
                        LOG.error("Request timeout, retiy times: %s" % self.timeout_retry)
                        raise TimeoutException()
            LOG.error("Should not go here")
            raise ClientException()

    def get_token(self):
        headers = {"Content-type": "application/json",
                   "Accept": "application/json"}

        payload = {
            "userName": self.username,
            "password": self.password
        }

        payload_json = json.dumps(payload)

        ret = self._process_request(headers,
                                    "POST",
                                    self.auth_url,
                                    payload_json)

        if ((ret.status_code >= requests.codes.ok) and
                (ret.status_code < requests.codes.multiple_choices)):
            if ret.content:
                result_data = json.loads(ret.content)
                token_id = (result_data["token"] + '.')[:-1]
                if token_id:
                    LOG.debug("authenticate successfully")
                    return token_id

        if ret.status_code == requests.codes.unauthorized:
            LOG.error("Terra dc authentication fail")
            raise AuthenticationException()

    def _decode_rensponse(self, response):
        try:
            if response.content.strip() != "":
                return json.loads(response.content)
            else:
                return {}
        except ValueError as e:
            with excutils.save_and_reraise_exception():
                LOG.debug("return body is not valid json string: %(e)s %(text)s",
                          {"e": e, "text": response.text}, exc_info=1)

    def _raise_for_status(self, resp):
        if resp.status_code == 400:
            raise BadRequestException(msg=resp.text)
        if resp.status_code == 404:
            raise NotFoundException(msg=resp.text)
        if 400 <= resp.status_code < 500:
            raise ClientException(msg=resp.text)
        elif 500 <= resp.status_code < 600:
            raise ServerErrorException(msg=resp.content)

    def _send(self, method, url, payload=None, decode=True, timeout=None):
        LOG.debug("Sending request: %(method)s %(url)s %(body)s",
                  {"method": method,
                   "url": url,
                   "body": payload})

        if not self.token:
            LOG.info("token is none, issue token")
            self.token = self.get_token()

        headers = {
            "content-type": "application/json",
            "Authorization": "Bear " + self.token
        }
        payload_json = json.dumps(payload)
        token_retry = self.token_retry + 1
        while token_retry:
            resp = self._process_request(headers, method, url, payload_json, timeout)
            if resp.status_code == requests.codes.unauthorized:
                if token_retry > 1:
                    LOG.error("Authentication fail, try again")
                    self.token = self.get_token()
                    token_retry -= 1
                    continue
                else:
                    LOG.error("Authentication fail.")
                    raise AuthenticationException()

            if resp.status_code != requests.codes.ok:
                msg = "Request to %s Failed with code %d, %s" % \
                      (resp.url, resp.status_code, resp.text)
                self._raise_for_status(resp)
            try:
                if decode:
                    return self._decode_rensponse(resp)
                else:
                    return resp.content
            except Exception as e:
                with excutils.save_and_reraise_exception():
                    LOG.error("%(method)s "
                              "%(url)s Failed. %(e)s"
                              "\nRequest body : [%(body)s] service",
                              {"method": method,
                               "url": url,
                               "e": e,
                               "body": payload_json})

    def _post(self, url, payload, timeout=None):
        return self._send("POST", url, payload, timeout=timeout)

    def _put(self, url, payload, timeout=None):
        return self._send("PUT", url, payload, timeout=timeout)

    def _get(self, url, timeout=None):
        return self._send("GET", url, timeout=timeout)

    def _delete(self, url, timeout=None):
        return self._send("DELETE", url, decode=False, timeout=timeout)

    def create_vni_range(self, tenant_id=None, start=None, end=None):
        payload = {
            "tenant_uuid": tenant_id,
            "start": start,
            "end": end
        }
        return self._post(self.url + "global_vni", payload)

    def delete_vni_range(self, id=None):
        return self._delete(self.url + "global_vni/" + id)

    def get_vni_range(self):
        return self._get(self.url + "global_vni/" + id)

    def create_network(self, id=None, tenant_id=None, name=None,
                       segment_id=None, network_type="vxlan",
                       external=False, distributed=False, dhcp_relay=None):
        network = {
            "id": id,
            "tenant_id": tenant_id,
            "name": name,
            "provider:segmentation_id": segment_id,
            "provider:network_type": network_type,
            "distributed": distributed,
            "router:external": external
        }
        if dhcp_relay:
            network["dhcp_relay"] = dhcp_relay
        payload = {"networks": [network]}
        return self._post(self.url + "networks", payload)

    def update_network(self):
        pass

    def delete_network(self, id):
        return self._delete(self.url + "networks/" + id)

    def create_subnet(self, id=None, tenant_id=None, name=None, network_id=None,
                      gateway_ip=None, cidr=None, enable_dhcp=False):
        subnet = {
            "id": id,
            "name": name,
            "network_id": network_id,
            "tenant_id": tenant_id,
            "ip_version": 4,
            "enable_dhcp": enable_dhcp
        }
        if gateway_ip:
            subnet["gateway_ip"] = gateway_ip
        if cidr:
            subnet["cidr"] = cidr
        payload = {"subnets": [subnet]}
        return self._post(self.url + "subnets", payload)

    def update_subnet(self):
        pass

    def delete_subnet(self, id):
        return self._delete(self.url + "subnets/" + id)

    def create_router(self, id=None, tenant_id=None, name=None,
                      segment_id=None, ecmp_number=3, aggregate_cidrs=None,
                      bgp_peers=None):
        router = {
            "id": id,
            "name": name,
            "tenant_id": tenant_id,
            "ecmp_number": ecmp_number,
            "aggregate_cidrs": aggregate_cidrs,
            # "bgp_peers": [
            #     {
            #         "ip_addr": "100.100.100.4",
            #         "as_number": "104",
            #         "device_name": "n9k-4",
            #         "advertise_host_route": False
            #     }
            # ],
        }
        if segment_id:
            router["provider:segmentation_id"] = segment_id
        if bgp_peers:
            router['bgp_peers'] = bgp_peers
        payload = {"routers": [router]}
        return self._post(self.url + "routers", payload)

    def update_router(self):
        pass

    def delete_router(self, id):
        return self._delete(self.url + "routers/" + id)

    def set_external_gateway(self, router_id, network_id, enable_snat, fixed_ips):
        payload = {'tenant_id': 'test', 'network_id': network_id, 'enable_snat': enable_snat, 'fixed_ips': fixed_ips}
        return self._put(self.url + "routers/" + router_id + "/external_gateway", {"external_gateway": payload})

    def clear_external_gateway(self, router_id):
        return self._delete(self.url + "routers/" + router_id + "/external_gateway")

    def add_router_interface(self, router_id, subnet_id):
        payload = {"subnet_id": subnet_id}
        return self._put(self.url + "routers/" + router_id + "/add_router_interface", payload)

    def del_router_interface(self, router_id, subnet_id):
        payload = {"subnet_id": subnet_id}
        return self._put(self.url + "routers/" + router_id + "/remove_router_interface", payload)

    def create_vlan_domain(self, id=None, name=None, start_vlan=None,
                           end_vlan=None, start_vxlan=None, end_vxlan=None):
        payload = {
            "domains":
                {"id": id,
                 "name": name,
                 "vlan_map_list":
                     [{"start_vlan": start_vlan,
                       "end_vlan": end_vlan,
                       "start_vxlan": start_vxlan,
                       "end_vxlan": end_vxlan}]
                 }}
        return self._post(self.url + "vlan_domains", payload)

    def delete_vlan_domain(self, id=None):
        return self._delete(self.url + "vlan_domains/" + id)

    def get_vlan_domain(self, id):
        return self._get(self.url + "vlan_domains/" + id)

    def create_port_binding(self, id=None, tenant_id=None, vlan_domain_id=None,
                            bind_port_list=None, untagged_vni=None):
        binding = {
            "id": id,
            "tenant_id": tenant_id,
            "vlan_domain_id": vlan_domain_id,
            "bind_port_list": bind_port_list
            # [{
            #     "device_name": "leaf-1",
            #     "port_name": "ethernet1/1"
            # }, {
            #     "device_name": "leaf-2",
            #     "port_name": "ethernet1/1"
            # }]
        }
        if untagged_vni is not None:
            binding['untagged_vni'] = untagged_vni

        return self._post(self.url + "port_vlan_domain_bindings",
                          {"bindings": [binding]},
                          timeout=30)

    def delete_port_binding(self, id):
        # return
        return self._delete(self.url + "port_vlan_domain_bindings/" + id,
                            timeout=30)

    def get_port_binding(self, id):
        # return
        return self._get(self.url + "port_vlan_domain_bindings/" + id,
                            timeout=30)

    def get_host_topology(self, host=None):
        url = self.url + "host"
        if host:
            url += "/%s" % host
        return self._get(url)

    def delete_host(self, host):
        url = self.url + "host/" + host
        return self._delete(url)

    def create_host(self, host, mgmt_ip, connections):
        url = self.url + "host"

        payload = {"vnetHostList": [{"name": host,
                                     "type": "host",
                                     "managementIpAddress": mgmt_ip,
                                     "connections": connections}]}

        return self._post(url, payload)
