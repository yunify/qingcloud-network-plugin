#!/usr/bin/evn python
# -*- coding: utf-8 -*-
import mox
import unittest
from networking_terra.ml2.mech_terra import TerraMechanismDriver
from oslo_config import cfg
from networking_terra.l3.terra_l3 import TerraL3RouterPlugin
from oslo_log import log as logging
from common.neutron_driver import NeutronDriver, BgpPeer,\
    NETWORK_TYPE_SUBINTERFACE
from networking_terra.qcext.qcext_terra import TerraQcExtDriver


LOG = logging.getLogger(__name__)


class TerraTestCases(unittest.TestCase):

    def setUp(self):
        super(TerraTestCases, self).setUp()
        self.m = mox.Mox()

    def tearDown(self):
        self.m.UnsetStubs()

    def test_vpc_0(self):
        # load settings
        cfg.CONF(["--config-file",
                  "/etc/ml2_conf_terra.ini"])

        vxnet_id = "vxnet-ks"
        vpc_id = "vpc-ks"
#         l3vni = 65534
#         l2vni = 65533
        l3vni = 11101
        l2vni = 10100

        bgp_subnet_map = {"Border-Leaf-92160.01":
                              {"ip_network": "169.254.1.0/24",
                               "network_id": "vxnet-ks_169.254.1.1",
                               "bgp_ip_addr": "169.254.1.1",
                               "interface_name": "Ethernet1/48",
                               },
                          "Border-Leaf-92160.02":
                              {"ip_network": "169.254.2.0/24",
                               "network_id": "vxnet-ks_169.254.2.1",
                               "bgp_ip_addr": "169.254.2.1",
                               "interface_name": "Ethernet1/48",
                               }}

        vlan_id = 511
        user_id = 'yunify'
        ip_network = "172.31.21.0/24"
        gateway_ip = "172.31.21.1"

        l3 = TerraL3RouterPlugin()
        ml2 = TerraMechanismDriver()
        ml2.initialize()
        qcext = TerraQcExtDriver()

        bgp_peers = [BgpPeer("169.254.1.2", 65535, "Border-Leaf-92160.01"),
                     BgpPeer("169.254.2.2", 65535, "Border-Leaf-92160.02")]

        driver = NeutronDriver(l3, ml2, qcext)

        driver.create_vpc(vpc_id, l3vni, user_id,
                          bgp_peers=bgp_peers)

        for bgp_peer in bgp_peers:
            switch_name = bgp_peer.device_name
            bgp_subnet = bgp_subnet_map[switch_name]
            _bgp_ip_addr = bgp_subnet["bgp_ip_addr"]
            _network_id = bgp_subnet["network_id"]
            _ip_network = bgp_subnet["ip_network"]
            _interface_name = bgp_subnet["interface_name"]

            driver.create_vxnet(_network_id, None, _ip_network,
                                _bgp_ip_addr, user_id,
                                network_type=NETWORK_TYPE_SUBINTERFACE)

            driver.add_subintf(vpc_id, _network_id,
                               _bgp_ip_addr, switch_name,
                               _interface_name, vlan_id,
                               user_id)

        driver.create_vxnet(vxnet_id, l2vni, ip_network, gateway_ip, user_id,
                            network_type='vxlan', enable_dhcp=True)
        driver.join_vpc(vpc_id, vxnet_id, user_id)

        driver.leave_vpc(vpc_id, vxnet_id, user_id)

        driver.delete_vxnet(vxnet_id, user_id)

        for bgp_peer in bgp_peers:
            switch_name = bgp_peer.device_name
            bgp_subnet = bgp_subnet_map[switch_name]
            _network_id = bgp_subnet["network_id"]

            driver.delete_subintf(vpc_id, _network_id)

            driver.delete_vxnet(_network_id, user_id)

        driver.delete_vpc(vpc_id, user_id)
