# Copyright 2011 VMware, Inc
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

from neutron_lib import exceptions as e

from neutron._i18n import _


class NeutronException(Exception):
    """Base Neutron Exception.

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.
    """
    message = _("An unknown exception occurred.")

    def __init__(self, **kwargs):
        try:
            super(NeutronException, self).__init__(self.message % kwargs)
            self.msg = self.message % kwargs
        except Exception:
            pass

    def __str__(self):
        return self.msg

    def use_fatal_exceptions(self):
        """Is the instance using fatal exceptions.

        :returns: Always returns False.
        """
        return False


class BadRequest(NeutronException):
    """An exception indicating a generic bad request for a said resource.

    A generic exception indicating a bad request for a specified resource.

    :param resource: The resource requested.
    :param msg: A message indicating why the request is bad.
    """
    message = _('Bad %(resource)s request: %(msg)s.')


class NotFound(NeutronException):
    """A generic not found exception."""
    pass


class Conflict(NeutronException):
    """A generic conflict exception."""
    pass


class NotAuthorized(NeutronException):
    """A generic not authorized exception."""
    message = _("Not authorized.")


class ServiceUnavailable(NeutronException):
    """A generic service unavailable exception."""
    message = _("The service is unavailable.")


class AdminRequired(NotAuthorized):
    """A not authorized exception indicating an admin is required.

    A specialization of the NotAuthorized exception that indicates and admin
    is required to carry out the operation or access a resource.

    :param reason: A message indicating additional details on why admin is
    required for the operation access.
    """
    message = _("User does not have admin privileges: %(reason)s.")


class ObjectNotFound(NotFound):
    """A not found exception indicating an identifiable object isn't found.

    A specialization of the NotFound exception indicating an object with a said
    ID doesn't exist.

    :param id: The ID of the (not found) object.
    """
    message = _("Object %(id)s not found.")


class NetworkNotFound(NotFound):
    """An exception indicating a network was not found.

    A specialization of the NotFound exception indicating a requested network
    could not be found.

    :param net_id: The UUID of the (not found) network requested.
    """
    message = _("Network %(net_id)s could not be found.")


class SubnetNotFound(NotFound):
    """An exception for a requested subnet that's not found.

    A specialization of the NotFound exception indicating a requested subnet
    could not be found.

    :param subnet_id: The UUID of the (not found) subnet that was requested.
    """
    message = _("Subnet %(subnet_id)s could not be found.")


class PortNotFound(NotFound):
    """An exception for a requested port that's not found.

    A specialization of the NotFound exception indicating a requested port
    could not be found.

    :param port_id: The UUID of the (not found) port that was requested.
    """
    message = _("Port %(port_id)s could not be found.")


class PortNotFoundOnNetwork(NotFound):
    """An exception for a requested port on a network that's not found.

    A specialization of the NotFound exception that indicates a specified
    port on a specified network doesn't exist.

    :param port_id: The UUID of the (not found) port that was requested.
    :param net_id: The UUID of the network that was requested for the port.
    """
    message = _("Port %(port_id)s could not be found "
                "on network %(net_id)s.")


class DeviceNotFoundError(NotFound):
    """An exception for a requested device that's not found.

    A specialization of the NotFound exception indicating a requested device
    could not be found.

    :param device_name: The name of the (not found) device that was requested.
    """
    message = _("Device '%(device_name)s' does not exist.")


class InUse(NeutronException):
    """A generic exception indicating a resource is already in use."""
    message = _("The resource is in use.")


class NetworkInUse(InUse):
    """An operational error indicating the network still has ports in use.

    A specialization of the InUse exception indicating a network operation was
    requested, but failed because there are still ports in use on the said
    network.

    :param net_id: The UUID of the network requested.
    """
    message = _("Unable to complete operation on network %(net_id)s. "
                "There are one or more ports still in use on the network.")


class SubnetInUse(InUse):
    """An operational error indicating a subnet is still in use.

    A specialization of the InUse exception indicating an operation failed
    on a subnet because the subnet is still in use.

    :param subnet_id: The UUID of the subnet requested.
    :param reason: Details on why the operation failed. If None, a default
    reason is used indicating one or more ports still have IP allocations
    on the subnet.
    """
    message = _("Unable to complete operation on subnet %(subnet_id)s: "
                "%(reason)s.")

    def __init__(self, **kwargs):
        if 'reason' not in kwargs:
            kwargs['reason'] = _("One or more ports have an IP allocation "
                                 "from this subnet")
        super(SubnetInUse, self).__init__(**kwargs)


class SubnetPoolInUse(InUse):
    """An operational error indicating a subnet pool is still in use.

    A specialization of the InUse exception indicating an operation failed
    on a subnet pool because it's still in use.

    :param subnet_pool_id: The UUID of the subnet pool requested.
    :param reason: Details on why the operation failed. If None a default
    reason is used indicating two or more concurrent subnets are allocated.
    """
    message = _("Unable to complete operation on subnet pool "
                "%(subnet_pool_id)s. %(reason)s.")

    def __init__(self, **kwargs):
        if 'reason' not in kwargs:
            kwargs['reason'] = _("Two or more concurrent subnets allocated")
        super(SubnetPoolInUse, self).__init__(**kwargs)


class PortInUse(InUse):
    """An operational error indicating a requested port is already attached.

    A specialization of the InUse exception indicating an operation failed on
    a port because it already has an attached device.

    :param port_id: The UUID of the port requested.
    :param net_id: The UUID of the requested port's network.
    :param device_id: The UUID of the device already attached to the port.
    """
    message = _("Unable to complete operation on port %(port_id)s "
                "for network %(net_id)s. Port already has an attached "
                "device %(device_id)s.")


class ServicePortInUse(InUse):
    """An error indicating a service port can't be deleted.

    A specialization of the InUse exception indicating a requested service
    port can't be deleted via the APIs.

    :param port_id: The UUID of the port requested.
    :param reason: Details on why the operation failed.
    """
    message = _("Port %(port_id)s cannot be deleted directly via the "
                "port API: %(reason)s.")


class PortBound(InUse):
    """An operational error indicating a port is already bound.

    A specialization of the InUse exception indicating an operation can't
    complete because the port is already bound.

    :param port_id: The UUID of the port requested.
    :param vif_type: The VIF type associated with the bound port.
    :param old_mac: The old MAC address of the port.
    :param net_mac: The new MAC address of the port.
    """
    message = _("Unable to complete operation on port %(port_id)s, "
                "port is already bound, port type: %(vif_type)s, "
                "old_mac %(old_mac)s, new_mac %(new_mac)s.")


class MacAddressInUse(InUse):
    """An network operational error indicating a MAC address is already in use.

    A specialization of the InUse exception indicating an operation failed
    on a network because a specified MAC address is already in use on that
    network.

    :param net_id: The UUID of the network.
    :param mac: The requested MAC address that's already in use.
    """
    message = _("Unable to complete operation for network %(net_id)s. "
                "The mac address %(mac)s is in use.")


class InvalidIpForNetwork(BadRequest):
    """An exception indicating an invalid IP was specified for a network.

    A specialization of the BadRequest exception indicating a specified IP
    address is invalid for a network.

    :param ip_address: The IP address that's invalid on the network.
    """
    message = _("IP address %(ip_address)s is not a valid IP "
                "for any of the subnets on the specified network.")


class InvalidIpForSubnet(BadRequest):
    """An exception indicating an invalid IP was specified for a subnet.

    A specialization of the BadRequest exception indicating a specified IP
    address is invalid for a subnet.

    :param ip_address: The IP address that's invalid on the subnet.
    """
    message = _("IP address %(ip_address)s is not a valid IP "
                "for the specified subnet.")


class IpAddressInUse(InUse):
    """An network operational error indicating an IP address is already in use.

    A specialization of the InUse exception indicating an operation can't
    complete because an IP address is in use.

    :param net_id: The UUID of the network.
    :param ip_address: The IP address that's already in use on the network.
    """
    message = _("Unable to complete operation for network %(net_id)s. "
                "The IP address %(ip_address)s is in use.")


class VlanIdInUse(InUse):
    """An exception indicating VLAN creation failed because it's already in use.

    A specialization of the InUse exception indicating network creation failed
    because a specified VLAN is already in use on the physical network.

    :param vlan_id: The LVAN ID.
    :param physical_network: The physical network.
    """
    message = _("Unable to create the network. "
                "The VLAN %(vlan_id)s on physical network "
                "%(physical_network)s is in use.")


class TunnelIdInUse(InUse):
    """A network creation failure due to tunnel ID already in use.

    A specialization of the InUse exception indicating network creation failed
    because a said tunnel ID is already in use.

    :param tunnel_id: The ID of the tunnel that's areadly in use.
    """
    message = _("Unable to create the network. "
                "The tunnel ID %(tunnel_id)s is in use.")


class ResourceExhausted(ServiceUnavailable):
    """A service uavailable error indicating a resource is exhausted."""
    pass


class NoNetworkAvailable(ResourceExhausted):
    """A failure to create a network due to no tenant networks for allocation.

    A specialization of the ResourceExhausted exception indicating network
    creation failed because no tenant network are available for allocation.
    """
    message = _("Unable to create the network. "
                "No tenant network is available for allocation.")


class SubnetMismatchForPort(BadRequest):
    """A bad request error indicating a specified subnet isn't on a port.

    A specialization of the BadRequest exception indicating a subnet on a port
    doesn't match a specified subnet.

    :param port_id: The UUID of the port.
    :param subnet_id: The UUID of the requested subnet.
    """
    message = _("Subnet on port %(port_id)s does not match "
                "the requested subnet %(subnet_id)s.")


class Invalid(NeutronException):
    """A generic base class for invalid errors."""
    def __init__(self, message=None):
        self.message = message
        super(Invalid, self).__init__()


class InvalidInput(BadRequest):
    """A bad request due to invalid input.

    A specialization of the BadRequest error indicating bad input was
    specified.

    :param error_message: Details on the operation that failed due to bad
    input.
    """
    message = _("Invalid input for operation: %(error_message)s.")


class IpAddressGenerationFailure(Conflict):
    """A conflict error due to no more IP addresses on a said network.

    :param net_id: The UUID of the network that has no more IP addresses.
    """
    message = _("No more IP addresses available on network %(net_id)s.")


class PreexistingDeviceFailure(NeutronException):
    """A creation error due to an already existing device.

    An exception indication creation failed due to an already existing
    device.

    :param dev_name: The device name that already exists.
    """
    message = _("Creation failed. %(dev_name)s already exists.")


class OverQuota(Conflict):
    """A error due to exceeding quota limits.

    A specialization of the Conflict exception indicating quota has been
    exceeded.

    :param overs: The resources that have exceeded quota.
    """
    message = _("Quota exceeded for resources: %(overs)s.")


class InvalidContentType(NeutronException):
    """An error due to invalid content type.

    :param content_type: The invalid content type.
    """
    message = _("Invalid content type %(content_type)s.")


class ExternalIpAddressExhausted(BadRequest):
    """An error due to not finding IP addresses on an external network.

    A specialization of the BadRequest exception indicating no IP addresses
    can be found on a network.

    :param net_id: The UUID of the network.
    """
    message = _("Unable to find any IP address on external "
                "network %(net_id)s.")


class TooManyExternalNetworks(NeutronException):
    """An error due to more than one external networks existing."""
    message = _("More than one external network exists.")


class InvalidConfigurationOption(NeutronException):
    """An error due to an invalid configuration option value.

    :param opt_name: The name of the configuration option that has an invalid
    value.
    :param opt_value: The value that's invalid for the configuration option.
    """
    message = _("An invalid value was provided for %(opt_name)s: "
                "%(opt_value)s.")


class NetworkTunnelRangeError(NeutronException):
    """An error due to an invalid network tunnel range.

    An exception indicating an invalid netowrk tunnel range was specified.

    :param tunnel_range: The invalid tunnel range. If specified in the
    start:end' format, they will be converted automatically.
    :param error: Additional details on why the range is invalid.
    """
    message = _("Invalid network tunnel range: "
                "'%(tunnel_range)s' - %(error)s.")

    def __init__(self, **kwargs):
        # Convert tunnel_range tuple to 'start:end' format for display
        if isinstance(kwargs['tunnel_range'], tuple):
            kwargs['tunnel_range'] = "%d:%d" % kwargs['tunnel_range']
        super(NetworkTunnelRangeError, self).__init__(**kwargs)


class PolicyInitError(NeutronException):
    """An error due to policy initialization failure.

    :param policy: The policy that failed to initialize.
    :param reason: Details on why the policy failed to initialize.
    """
    message = _("Failed to initialize policy %(policy)s because %(reason)s.")


class PolicyCheckError(NeutronException):
    """An error due to a policy check failure.

    :param policy: The policy that failed to check.
    :param reason: Additional details on the failure.
    """
    message = _("Failed to check policy %(policy)s because %(reason)s.")


class MultipleExceptions(Exception):
    """Container for multiple exceptions encountered.

    The API layer of Neutron will automatically unpack, translate,
    filter, and combine the inner exceptions in any exception derived
    from this class.
    """

    def __init__(self, exceptions, *args, **kwargs):
        """Create a new instance wrapping the exceptions.

        :param exceptions: The inner exceptions this instance is composed of.
        :param args: Passed onto parent constructor.
        :param kwargs: Passed onto parent constructor.
        """
        super(MultipleExceptions, self).__init__(*args, **kwargs)
        self.inner_exceptions = exceptions


class SubnetPoolNotFound(e.NotFound):
    message = _("Subnet pool %(subnetpool_id)s could not be found.")


class QosPolicyNotFound(e.NotFound):
    message = _("QoS policy %(policy_id)s could not be found.")


class QosRuleNotFound(e.NotFound):
    message = _("QoS rule %(rule_id)s for policy %(policy_id)s "
                "could not be found.")


class PortQosBindingNotFound(e.NotFound):
    message = _("QoS binding for port %(port_id)s and policy %(policy_id)s "
                "could not be found.")


class NetworkQosBindingNotFound(e.NotFound):
    message = _("QoS binding for network %(net_id)s and policy %(policy_id)s "
                "could not be found.")


class PlacementEndpointNotFound(e.NotFound):
    message = _("Placement API endpoint not found")


class PlacementResourceProviderNotFound(e.NotFound):
    message = _("Placement resource provider not found %(resource_provider)s.")


class PlacementInventoryNotFound(e.NotFound):
    message = _("Placement inventory not found for resource provider "
                "%(resource_provider)s, resource class %(resource_class)s.")


class PlacementAggregateNotFound(e.NotFound):
    message = _("Aggregate not found for resource provider "
                "%(resource_provider)s.")


class PolicyRemoveAuthorizationError(e.NotAuthorized):
    message = _("Failed to remove provided policy %(policy_id)s "
                "because you are not authorized.")


class StateInvalid(e.BadRequest):
    message = _("Unsupported port state: %(port_state)s.")


class QosPolicyInUse(e.InUse):
    message = _("QoS Policy %(policy_id)s is used by "
                "%(object_type)s %(object_id)s.")


class DhcpPortInUse(e.InUse):
    message = _("Port %(port_id)s is already acquired by another DHCP agent")


class HostRoutesExhausted(e.BadRequest):
    # NOTE(xchenum): probably make sense to use quota exceeded exception?
    message = _("Unable to complete operation for %(subnet_id)s. "
                "The number of host routes exceeds the limit %(quota)s.")


class DNSNameServersExhausted(e.BadRequest):
    # NOTE(xchenum): probably make sense to use quota exceeded exception?
    message = _("Unable to complete operation for %(subnet_id)s. "
                "The number of DNS nameservers exceeds the limit %(quota)s.")


class FlatNetworkInUse(e.InUse):
    message = _("Unable to create the flat network. "
                "Physical network %(physical_network)s is in use.")


class TenantNetworksDisabled(e.ServiceUnavailable):
    message = _("Tenant network creation is not enabled.")


class NoNetworkFoundInMaximumAllowedAttempts(e.ServiceUnavailable):
    message = _("Unable to create the network. "
                "No available network found in maximum allowed attempts.")


class MalformedRequestBody(e.BadRequest):
    message = _("Malformed request body: %(reason)s.")


class InvalidAllocationPool(e.BadRequest):
    message = _("The allocation pool %(pool)s is not valid.")


class UnsupportedPortDeviceOwner(e.Conflict):
    message = _("Operation %(op)s is not supported for device_owner "
                "%(device_owner)s on port %(port_id)s.")


class OverlappingAllocationPools(e.Conflict):
    message = _("Found overlapping allocation pools: "
                "%(pool_1)s %(pool_2)s for subnet %(subnet_cidr)s.")


class PlacementInventoryUpdateConflict(e.Conflict):
    message = _("Placement inventory update conflict for resource provider "
                "%(resource_provider)s, resource class %(resource_class)s.")


class OutOfBoundsAllocationPool(e.BadRequest):
    message = _("The allocation pool %(pool)s spans "
                "beyond the subnet cidr %(subnet_cidr)s.")


class MacAddressGenerationFailure(e.ServiceUnavailable):
    message = _("Unable to generate unique mac on network %(net_id)s.")


class BridgeDoesNotExist(e.NeutronException):
    message = _("Bridge %(bridge)s does not exist.")


class QuotaResourceUnknown(e.NotFound):
    message = _("Unknown quota resources %(unknown)s.")


class QuotaMissingTenant(e.BadRequest):
    message = _("Tenant-id was missing from quota request.")


class InvalidQuotaValue(e.Conflict):
    message = _("Change would make usage less than 0 for the following "
                "resources: %(unders)s.")


class InvalidSharedSetting(e.Conflict):
    message = _("Unable to reconfigure sharing settings for network "
                "%(network)s. Multiple tenants are using it.")


class InvalidExtensionEnv(e.BadRequest):
    message = _("Invalid extension environment: %(reason)s.")


class ExtensionsNotFound(e.NotFound):
    message = _("Extensions not found: %(extensions)s.")


class GatewayConflictWithAllocationPools(e.InUse):
    message = _("Gateway ip %(ip_address)s conflicts with "
                "allocation pool %(pool)s.")


class GatewayIpInUse(e.InUse):
    message = _("Current gateway ip %(ip_address)s already in use "
                "by port %(port_id)s. Unable to update.")


class NetworkVlanRangeError(e.NeutronException):
    message = _("Invalid network VLAN range: '%(vlan_range)s' - '%(error)s'.")

    def __init__(self, **kwargs):
        # Convert vlan_range tuple to 'start:end' format for display
        if isinstance(kwargs['vlan_range'], tuple):
            kwargs['vlan_range'] = "%d:%d" % kwargs['vlan_range']
        super(NetworkVlanRangeError, self).__init__(**kwargs)


class PhysicalNetworkNameError(e.NeutronException):
    message = _("Empty physical network name.")


class NetworkVxlanPortRangeError(e.NeutronException):
    message = _("Invalid network VXLAN port range: '%(vxlan_range)s'.")


class VxlanNetworkUnsupported(e.NeutronException):
    message = _("VXLAN network unsupported.")


class DuplicatedExtension(e.NeutronException):
    message = _("Found duplicate extension: %(alias)s.")


class DeviceIDNotOwnedByTenant(e.Conflict):
    message = _("The following device_id %(device_id)s is not owned by your "
                "tenant or matches another tenants router.")


class InvalidCIDR(e.BadRequest):
    message = _("Invalid CIDR %(input)s given as IP prefix.")


class RouterNotCompatibleWithAgent(e.NeutronException):
    message = _("Router '%(router_id)s' is not compatible with this agent.")


class DvrHaRouterNotSupported(e.NeutronException):
    message = _("Router '%(router_id)s' cannot be both DVR and HA.")


class FailToDropPrivilegesExit(SystemExit):
    """Exit exception raised when a drop privileges action fails."""
    code = 99


class FloatingIpSetupException(e.NeutronException):
    def __init__(self, message=None):
        self.message = message
        super(FloatingIpSetupException, self).__init__()


class IpTablesApplyException(e.NeutronException):
    def __init__(self, message=None):
        self.message = message
        super(IpTablesApplyException, self).__init__()


class NetworkIdOrRouterIdRequiredError(e.NeutronException):
    message = _('Both network_id and router_id are None. '
                'One must be provided.')


class AbortSyncRouters(e.NeutronException):
    message = _("Aborting periodic_sync_routers_task due to an error.")


class MissingMinSubnetPoolPrefix(e.BadRequest):
    message = _("Unspecified minimum subnet pool prefix.")


class EmptySubnetPoolPrefixList(e.BadRequest):
    message = _("Empty subnet pool prefix list.")


class PrefixVersionMismatch(e.BadRequest):
    message = _("Cannot mix IPv4 and IPv6 prefixes in a subnet pool.")


class UnsupportedMinSubnetPoolPrefix(e.BadRequest):
    message = _("Prefix '%(prefix)s' not supported in IPv%(version)s pool.")


class IllegalSubnetPoolPrefixBounds(e.BadRequest):
    message = _("Illegal prefix bounds: %(prefix_type)s=%(prefixlen)s, "
                "%(base_prefix_type)s=%(base_prefixlen)s.")


class IllegalSubnetPoolPrefixUpdate(e.BadRequest):
    message = _("Illegal update to prefixes: %(msg)s.")


class SubnetAllocationError(e.NeutronException):
    message = _("Failed to allocate subnet: %(reason)s.")


class AddressScopePrefixConflict(e.Conflict):
    message = _("Failed to associate address scope: subnetpools "
                "within an address scope must have unique prefixes.")


class IllegalSubnetPoolAssociationToAddressScope(e.BadRequest):
    message = _("Illegal subnetpool association: subnetpool %(subnetpool_id)s "
                "cannot be associated with address scope "
                "%(address_scope_id)s.")


class IllegalSubnetPoolIpVersionAssociationToAddressScope(e.BadRequest):
    message = _("Illegal subnetpool association: subnetpool %(subnetpool_id)s "
                "cannot associate with address scope %(address_scope_id)s "
                "because subnetpool ip_version is not %(ip_version)s.")


class IllegalSubnetPoolUpdate(e.BadRequest):
    message = _("Illegal subnetpool update : %(reason)s.")


class MinPrefixSubnetAllocationError(e.BadRequest):
    message = _("Unable to allocate subnet with prefix length %(prefixlen)s, "
                "minimum allowed prefix is %(min_prefixlen)s.")


class MaxPrefixSubnetAllocationError(e.BadRequest):
    message = _("Unable to allocate subnet with prefix length %(prefixlen)s, "
                "maximum allowed prefix is %(max_prefixlen)s.")


class SubnetPoolDeleteError(e.BadRequest):
    message = _("Unable to delete subnet pool: %(reason)s.")


class SubnetPoolQuotaExceeded(e.OverQuota):
    message = _("Per-tenant subnet pool prefix quota exceeded.")


class NetworkSubnetPoolAffinityError(e.BadRequest):
    message = _("Subnets hosted on the same network must be allocated from "
                "the same subnet pool.")


class ObjectActionError(e.NeutronException):
    message = _('Object action %(action)s failed because: %(reason)s.')


class CTZoneExhaustedError(e.NeutronException):
    message = _("IPtables conntrack zones exhausted, iptables rules cannot "
                "be applied.")


class TenantQuotaNotFound(e.NotFound):
    message = _("Quota for tenant %(tenant_id)s could not be found.")


class TenantIdProjectIdFilterConflict(e.BadRequest):
    message = _("Both tenant_id and project_id passed as filters.")
