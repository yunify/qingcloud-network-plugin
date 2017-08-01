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
from oslo_log import log as logging
from oslo_utils import excutils
import json
import requests
import traceback
import threading
from requests import exceptions as r_exec

from networking_terra.common.exceptions import AuthenticationException, \
    InitializException, TimeoutException, ClientException, \
    ServerErrorException, BadRequestException, NotFoundException, \
    HTTPErrorException
from contextlib import contextmanager

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
        if not cfg.CONF.ml2_terra.origin_name:
            raise InitializException(msg="Terra dc origin_name must be configured")

        return cls(
            cfg.CONF.ml2_terra.url,
            cfg.CONF.ml2_terra.auth_url,
            cfg.CONF.ml2_terra.username,
            cfg.CONF.ml2_terra.password,
            cfg.CONF.ml2_terra.http_timeout,
            cfg.CONF.ml2_terra.origin_name)

    def __init__(self, url, auth_url, username, password, timeout, origin_name):
        if url.endswith("/"):
            self.url = url
        else:
            self.url = url + "/"
        self.auth_url = auth_url
        self.username = username
        self.password = password
        self.timeout = timeout
        self.origin_name = origin_name
        self.token = None
        self.timeout_retry = 1
        self.token_retry = 1
        self.lock = threading.RLock()

    def _process_request(self, headers, method, url, payload_json, timeout=None):
        LOG.debug("Sending request: %(method)s %(url)s %(body)s",
                  {"method": method,
                   "url": url,
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
            except (r_exec.Timeout, r_exec.ConnectionError) as e:
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
            raise BadRequestException(msg=resp.content)
        if resp.status_code == 404:
            raise NotFoundException(msg=resp.content)
        if 400 <= resp.status_code < 500:
            raise ClientException(msg=resp.content)
        elif 500 <= resp.status_code < 600:
            raise ServerErrorException(msg=resp.content)
        raise HTTPErrorException(msg="return code: %s" % resp.status_code)

    def is_response_ok(self, resp):
        if resp.status_code == 200 \
                or resp.status_code == 201 \
                or resp.status_code == 204:
            return True
        return False

    def _send(self, method, url, payload=None, decode=True, timeout=None):
        payload_json = json.dumps(payload)
        token_retry = self.token_retry + 1
        while token_retry:

            _token = None
            with self._lock():
                if not self.token:
                    LOG.info("token is none, issue token")
                    self.token = self.get_token()

                _token = self.token

            if not _token:
                LOG.error("fail to get token")
                raise AuthenticationException()

            headers = {
                "content-type": "application/json",
                "Authorization": "Bear " + _token
            }
            resp = self._process_request(headers, method, url, payload_json,
                                         timeout)
            if resp.status_code == requests.codes.unauthorized:
                if token_retry > 1:
                    with self._lock():
                        LOG.error("Authentication fail, try again")
                        if _token == self.token:
                            self.token = None
                    token_retry -= 1
                    continue
                else:
                    LOG.error("Authentication fail.")
                    raise AuthenticationException()

            if not self.is_response_ok(resp):
                LOG.error("Request to %s Failed with code %d, %s" % \
                          (resp.url, resp.status_code, resp.text))
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

    def _post(self, url, payload=None, timeout=None):
        return self._send("POST", url, payload, timeout=timeout)

    def _put(self, url, payload, timeout=None):
        return self._send("PUT", url, payload, timeout=timeout)

    def _get(self, url, timeout=None):
        return self._send("GET", url, timeout=timeout)

    def _delete(self, url, timeout=None):
        return self._send("DELETE", url, decode=False, timeout=timeout)

    def create_vni_range(self, name=None, start=None, end=None):
        vni_pool = {
            "name": name,
            "vni_ranges": [
                {
                    "start": start,
                    "end": end
                }
            ]
        }
        payload = {"vni_pool": [vni_pool]}
        return self._post(self.url + "global_vni", payload)

    def delete_vni_range(self, id=None):
        return self._delete(self.url + "vni_pools/%s" % id)

    def get_vni_range(self, id=None):
        return self._get(self.url + "vni_pools/%s" % id)

    def get_vni_pools(self):
        return self._get(self.url + "vni_pools")

    def create_tenant(self, tenant_id, tenant_name=None):
        try:
            tenant_url = self.url + "tenants"
            tenant = {
                "name": tenant_name,
                "origin": self.origin_name,
                "original_id": tenant_id,
                "description": "Created by %s" % self.origin_name
            }
            return self._post(tenant_url, tenant)
        except Exception as e:
            LOG.error("create tenant error: %s" % e.msg)
            LOG.error(traceback.format_exc())

    def get_or_create_tenant_by_original_id(self, tenant_id, tenant_name):
        try:
            return self.get_id_by_original_id("tenants", tenant_id)
        except NotFoundException:
            LOG.info("tenant not found, create")
            return self.create_tenant(tenant_id, tenant_name)['id']

    def get_id_by_original_id(self, resource, original_id):
        if not original_id:
            return None
        url = "%s%s?origin=%s&original_id=%s" % (self.url, resource, self.origin_name, original_id)
        ret = self._get(url)
        if not ret or not ret[0].get("id"):
            LOG.warn("%s %s not found" % (resource, original_id))
            raise NotFoundException(msg="%s %s" % (resource, original_id))
        return ret[0]["id"]

    def create_network(self, name, original_id=None,
                       tenant_id=None, tenant_name=None,
                       segment_type="vxlan", segment_global_id=None, segment_local_id=None,
                       router_external=False, vni_pool_name=None):
        tenant_id = self.get_or_create_tenant_by_original_id(tenant_id, tenant_name)

        network = {
            'name': name,
            "origin": self.origin_name,
            'original_id': original_id,
            'tenant_id': tenant_id,
            'segment:type': segment_type,
            "router:external": router_external,
            "segment:global_id_pool_name": vni_pool_name
        }
        if segment_global_id:
            network["segment:global_id"] = segment_global_id
        if segment_local_id:
            network["segment_local_id"] = segment_local_id
        return self._post(self.url + "networks", network)

    def update_network(self, id, name=None, original_id=None,
                       tenant_id=None, tenant_name=None,
                       segment_type="vxlan", segment_global_id=None, segment_local_id=None,
                       router_external=True):
        tenant_id = self.get_or_create_tenant_by_original_id(tenant_id, tenant_name)
        network = {
            'name': name,
            "origin": self.origin_name,
            'original_id': original_id,
            'tenant_id': tenant_id,
            'segment:type': segment_type,
            # 'segment: global_id': segment_global_id,
            # 'segment:local_id': segment_local_id,
            "router:external": router_external
        }
        if segment_global_id:
            network["segment:global_id"] = segment_global_id
        if segment_local_id:
            network["segment_local_id"] = segment_local_id
        return self._put(self.url + "networks/%s" % id, network)

    def delete_network(self, id):
        id = self.get_id_by_original_id("networks", id)
        return self._delete(self.url + "networks/%s" % id)

    def create_subnet(self, name, original_id=None,
                      tenant_id=None, tenant_name=None, network_id=None,
                      ip_version=None, cidr=None, gateway_ip=None, enable_dhcp=True):
        tenant_id = self.get_or_create_tenant_by_original_id(tenant_id, tenant_name)
        network_id = self.get_id_by_original_id("networks", network_id)
        subnet = {
            "name": name,
            "origin": self.origin_name,
            "original_id": original_id,
            "tenant_id": tenant_id,
            "network_id": network_id,
            "enable_dhcp": enable_dhcp
        }
        if ip_version:
            subnet["ip_version"] = ip_version
        if gateway_ip:
            subnet["gateway_ip"] = gateway_ip
        if cidr:
            subnet["cidr"] = cidr
        return self._post(self.url + "subnets", subnet)

    def update_subnet(self, id, name=None, original_id=None,
                      tenant_id=None, tenant_name=None, network_id=None,
                      ip_version=None, cidr=None, gateway_ip=None, enable_dhcp=True):
        tenant_id = self.get_or_create_tenant_by_original_id(tenant_id, tenant_name)
        network_id = self.get_id_by_original_id("networks", network_id)
        subnet = {
            "name": name,
            "origin": self.origin_name,
            "original_id": original_id,
            "tenant_id": tenant_id,
            "network_id": network_id,
            "enable_dhcp": enable_dhcp
        }
        if ip_version:
            subnet["ip_version"] = ip_version
        if gateway_ip:
            subnet["gateway_ip"] = gateway_ip
        if cidr:
            subnet["cidr"] = cidr
        return self._put(self.url + "subnets/%s" % id, subnet)

    def delete_subnet(self, id):
        id = self.get_id_by_original_id("subnets", id)
        return self._delete(self.url + "subnets/%s" % id)

    def create_router(self, name=None, tenant_id=None,
                      tenant_name=None, original_id=None, ports=None, l3_vni=None,
                      vni_pool_name=None):
        tenant_id = self.get_or_create_tenant_by_original_id(tenant_id, tenant_name)
        router = {
            "name": name,
            "origin": self.origin_name,
            "original_id": original_id,
            "tenant_id": tenant_id,
            "cisco:l3_vni": l3_vni,
            "cisco:l3_vni_pool_name": vni_pool_name
        }
        if ports:
            router["ports"] = ports
        return self._post(self.url + "routers", router)

    def update_router(self, id, name=None, original_id=None,
                      tenant_id=None, tenant_name=None, ports=None, network_id=None,
                      enable_snat=True, fixed_ips=None, cisco_l3_vni=0):
        tenant_id = self.get_or_create_tenant_by_original_id(tenant_id, tenant_name)
        router = {
            "name": name,
            "origin": self.origin_name,
            "original_id": original_id,
            "tenant_id": tenant_id,
            "gateway": {
                "network_id": network_id,
                "enable_snat": enable_snat,
                "fixed_ips": fixed_ips,
            },
            "cisco:l3_vni": cisco_l3_vni
        }
        if ports:
            router["ports"] = ports
        payload = {"router": [router]}
        return self._put(self.url + "routers/%s" % id, payload)

    def delete_router(self, id):
        id = self.get_id_by_original_id("routers", id)
        return self._delete(self.url + "routers/%s" % id)

    def add_router_bgp_peer(self, router_id, as_number, ip_address, device_name,
                            advertise_host_route=False):
        router_id = self.get_id_by_original_id("routers", router_id)
        switch = self.get_switch(device_name)
        payload = {
            "device_id": switch["id"],
            "as_number": as_number,
            "ip_address": ip_address,
            "advertise_host_route": advertise_host_route
        }
        return self._post(self.url + "routers/%s/bgp_neighbors" % router_id, payload)

    def get_router_bgp_peers(self, router_id):
        router_id = self.get_id_by_original_id("routers", router_id)
        return self._get(self.url + "routers/%s/bgp_neighbors" % router_id)

    def delete_router_bgp_peer(self, router_id, peer_id):
        router_id = self.get_id_by_original_id("routers", router_id)
        return self._delete(self.url + "routers/%s/bgp_neighbors/%s" % (router_id, peer_id))

    def set_external_gateway(self, router_id, network_id, enable_snat, fixed_ips):
        external_gateway = {'network_id': network_id, 'enable_snat': enable_snat, 'fixed_ips': fixed_ips}
        payload = {"external_gateways": [external_gateway]}
        return self._put(self.url + "routers/%s/external_gateway" % router_id, payload)

    def clear_external_gateway(self, router_id):
        return self._delete(self.url + "routers/%s/external_gateway" % router_id)

    def add_router_interface(self, router_id, subnet_id, port_id):
        port_id = self.get_id_by_original_id("ports", port_id)
        router_id = self.get_id_by_original_id("routers", router_id)
        subnet_id = self.get_id_by_original_id("subnets", subnet_id)
        interface = {
            "subnet_id": subnet_id,
            "port_id": port_id
        }
        return self._post(self.url + "routers/%s/add_interfaces" % router_id, interface)

    def del_router_interface(self, router_id, subnet_id, port_id=None):
        port_id = self.get_id_by_original_id("ports", port_id)
        router_id = self.get_id_by_original_id("routers", router_id)
        subnet_id = self.get_id_by_original_id("subnets", subnet_id)
        interface = {
            "subnet_id": subnet_id,
            "port_id": port_id
        }
        return self._post(self.url + "routers/%s/remove_interfaces" % router_id, interface)

    def _get_fixed_ips(self, fixed_ips):
        for ip in fixed_ips:
            ip["subnet_id"] = self.get_id_by_original_id("subnets", ip["subnet_id"])
        return fixed_ips

    def create_direct_port(self, name, original_id=None,
                           tenant_id=None, tenant_name=None, network_id=None,
                           fixed_ips=None, switch_interface_id=None, vlan_id=None):
        tenant_id = self.get_or_create_tenant_by_original_id(tenant_id, tenant_name)
        network_id = self.get_id_by_original_id("networks", network_id)
        port = {
            "name": name,
            "origin": self.origin_name,
            "original_id": original_id,
            "tenant_id": tenant_id,
            "network_id": network_id,
            "ips": self._get_fixed_ips(fixed_ips),
            "direct_port": {
                "switch_interface_id": switch_interface_id,
                "vlan_id": vlan_id
            }
        }
        return self._post(self.url + "ports", port)

    def create_port(self, name, original_id=None,
                    tenant_id=None, tenant_name=None, network_id=None,
                    fixed_ips=None):
        tenant_id = self.get_or_create_tenant_by_original_id(tenant_id, tenant_name)
        network_id = self.get_id_by_original_id("networks", network_id)
        port = {
            "name": name,
            "origin": self.origin_name,
            "original_id": original_id,
            "tenant_id": tenant_id,
            "network_id": network_id,
            "ips": self._get_fixed_ips(fixed_ips),
        }
        return self._post(self.url + "ports", port)

    def update_port(self, name, original_id=None,
                    tenant_id=None, tenant_name=None, network_id=None,
                    subnet_id=None, ip_address=None):
        tenant_id = self.get_or_create_tenant_by_original_id(tenant_id, tenant_name)
        network_id = self.get_id_by_original_id("networks", network_id)
        subnet_id = self.get_id_by_original_id("subnets", subnet_id)
        port = {
            "name": name,
            "origin": self.origin_name,
            "original_id": original_id,
            "tenant_id": tenant_id,
            "network_id": network_id,
            "ips": [
                {
                    "subnet_id": subnet_id,
                    "ip_address": ip_address
                }
            ]
        }
        return self._put(self.url + "ports", port)

    def delete_port(self, id):
        id = self.get_id_by_original_id("ports", id)
        return self._delete(self.url + "ports/%s" % id)

    def port_bind(self, port_id=None, switch_name=None, interface_name=None, vlan_native=False):
        port_id = self.get_id_by_original_id("ports", port_id)
        binding = {
            "switch_name": switch_name,
            "interface_name": interface_name,
            "vlan_native": vlan_native
        }
        return self._post(self.url + "ports/%s/bind" % port_id, binding)

    def create_port_binding(self, network_id=None, switch_name=None, interface_name=None,
                            vlan_native=False, local_vlan_id=None):
        network_id = self.get_id_by_original_id("networks", network_id)
        binding = {
            "network_id": network_id,
            "switch_name": switch_name,
            "interface_name": interface_name,
            "vlan_native": vlan_native
        }
        if local_vlan_id:
            binding["local_vlan_id"] = local_vlan_id
        return self._post(self.url + "port_bindings", binding)

    def get_port_binding(self, network_id, switch_name, interface_name):
        url = self.url + "port_bindings?switch_name=%s&interface_name=%s" % \
                (switch_name, interface_name)

        if network_id:
            network_id = self.get_id_by_original_id("networks", network_id)
            url += "&network_id=%s" % network_id

        bindings = self._get(url)

        if not bindings:
            msg = "binding not found for network %s, switch %s, interface %s" % \
                  (network_id, switch_name, interface_name)
            LOG.error(msg)
            raise NotFoundException(msg=msg)
        return bindings[0]

    def delete_port_binding(self, network_id, switch_name, interface_name):
        binding = self.get_port_binding(network_id, switch_name, interface_name)
        return self._delete(self.url + "port_bindings/%s" % binding['id'])

    def port_unbind(self, id):
        port_id = self.get_id_by_original_id("ports", id)
        return self._post(self.url + "ports/%s/unbind" % port_id)

    def get_host(self, id):
        return self._get(self.url + "hosts/%s" % id)

    @contextmanager
    def _lock(self):
        self.lock.acquire()
        try:
            yield
        except Exception, e:
            LOG.exception("yield exits with exception: %s" % e)
        self.lock.release()

    def get_host_by_name(self, hostname):
        hosts = self._get(self.url + "hosts?hostname=%s" % hostname)
        if not hosts:
            return None
        return hosts[0]

    def create_host(self, hostname, mgmt_ip):
        host = {
            "hostname": hostname,
            "host_ip": mgmt_ip
        }
        return self._post(self.url + "hosts", host)

    def delete_host(self, id):
        return self._delete(self.url + "hosts/%s" % id)

    def add_host_links(self, links):
        body = []
        for link in links:
            body.append({
                "host_name": link["host_name"],
                "host_interface_name": link["host_interface_name"],
                "switch_name": link["switch_name"],
                "switch_interface_name": link["switch_interface_name"]
            })
        return self._post(self.url + "host_links", body)

    def get_host_links_by_hostname(self, hostname):
        mapping = self._get(self.url + "host_links?host_name=%s" % hostname)
        return mapping

    def delete_host_link(self, id):
        return self._delete(self.url + "host_links/%s" % id)

    def get_switch_interface(self, switch_name, interface_name):
        switches = self._get(self.url + "devices?name=%s" % switch_name)
        if switches:
            switch = switches[0]
            if "interfaces" in switch:
                for intf in switch["interfaces"]:
                    if intf.get("name") == interface_name:
                        return intf
        msg = "can't find interface: %s %s" % (switch_name, interface_name)
        LOG.error(msg)
        raise NotFoundException(msg=msg)

    def get_switch(self, switch_name):
        query_url = self.url + "devices?name=%s" % switch_name
        switches = self._get(query_url)
        if not switches:
            raise NotFoundException(msg="switch %s not found" % switch_name)
        return switches[0]
