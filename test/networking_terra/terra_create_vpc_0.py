#!/usr/bin/evn python
# -*- coding: utf-8 -*-
import mox
import unittest
from networking_terra.ml2.mech_terra import TerraMechanismDriver
from oslo_config import cfg
from networking_terra.l3.terra_l3 import TerraL3RouterPlugin
from oslo_log import log as logging
from common.neutron_driver import NeutronDriver, BgpPeer
import netaddr


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

        vxnet_id = "vxnet-0"
        vpc_id = "vpc-0"
        l3vni = 65534
        l2vni = 65533
        bgp_subnet_map = {"Border-Leaf-92160.01":
                                {"l2vni": 65531,
                                 "ip_network": "169.254.1.0/24",
                                 "network_id": "vxnet-0_169.254.1.1",
                                 "bgp_ip_addr": "169.254.1.1"
                                 },
                          "Border-Leaf-92160.02":
                                {"l2vni": 65532,
                                 "ip_network": "169.254.2.0/24",
                                 "network_id": "vxnet-0_169.254.2.1",
                                 "bgp_ip_addr": "169.254.2.1"
                                 }}

        vlan_id = 511
        user_id = 'yunify'
        ip_network = "172.31.21.0/24"
        gateway_ip = "172.31.21.1"

        l3 = TerraL3RouterPlugin()
        ml2 = TerraMechanismDriver()
        ml2.initialize()

        bgp_peers = [BgpPeer("169.254.1.2", 65535, "Border-Leaf-92160.01"),
                     BgpPeer("169.254.2.2", 65535, "Border-Leaf-92160.02")]
        driver = NeutronDriver(l3, ml2, None)
        driver.create_vpc(vpc_id, l3vni, user_id,
                          bgp_peers=bgp_peers)

        for bgp_peer in bgp_peers:
            switch_id = bgp_peer.device_name
            bgp_subnet = bgp_subnet_map[switch_id]
            _bgp_ip_addr = bgp_subnet["bgp_ip_addr"]
            _network_id = bgp_subnet["network_id"]
            _l2vni = bgp_subnet["l2vni"]
            _ip_network = bgp_subnet["ip_network"]

            driver.create_vxnet(_network_id, _l2vni, _ip_network,
                                _bgp_ip_addr, user_id,
                                network_type='subintf')

            driver.join_vpc(vpc_id, _network_id, user_id)

            driver.add_node(_network_id, _l2vni, switch_id,
                            user_id,
                            vlan_id,
                            native_vlan=False)

        driver.create_vxnet(vxnet_id, l2vni, ip_network, gateway_ip, user_id,
                            network_type='vxlan', enable_dhcp=True)
        driver.join_vpc(vpc_id, vxnet_id, user_id)

#             driver.remove_node(subnet_id, switch_id, user_id)
# #      
#             driver.leave_vpc(vpc_id, subnet_id, user_id)
#             driver.delete_vxnet(subnet_id, user_id)
# # 
#         driver.leave_vpc(vpc_id, vxnet_id, user_id)
#         driver.delete_vxnet(vxnet_id, user_id)
# 
#         vxnet_id='vxnet-r0fsbmw'
#         driver.leave_vpc(vpc_id, vxnet_id, user_id)
#         driver.delete_vxnet(vxnet_id, user_id)
# 
#         # cisco need roughly 10s to delete l3vni
#         # need 10s interval when run this test repeatly
#         driver.delete_vpc(vpc_id, user_id)
