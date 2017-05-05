#!/usr/bin/evn python
# -*- coding: utf-8 -*-
import mox
import unittest
from networking_terra.ml2.mech_terra import TerraMechanismDriver
from oslo_config import cfg
from networking_terra.l3.terra_l3 import TerraL3RouterPlugin
from oslo_log import log as logging
from common.neutron_driver import NeutronDriver


LOG = logging.getLogger(__name__)


class TerraTestCases(unittest.TestCase):

    def setUp(self):
        super(TerraTestCases, self).setUp()
        self.m = mox.Mox()

    def tearDown(self):
        self.m.UnsetStubs()

    def test_TerraDriver(self):

        # load settings
        cfg.CONF(["--config-file",
                  "/etc/ml2_conf_terra.ini"])

        vxnet_id = "vxnet-123456"
        router_id = "rtr-123456"
        l3vni = 12001
        l2vni = 11001
        user_id = 'usr-123456'
        ip_network = '192.168.0.0/24'
        gateway_ip = '192.168.0.1'
        host = 'tr03n02'

        l3 = TerraL3RouterPlugin()
        ml2 = TerraMechanismDriver()
        ml2.initialize()

        driver = NeutronDriver(l3, ml2)
        driver.create_vpc(router_id, l3vni, user_id)

        driver.create_vxnet(vxnet_id, l2vni, ip_network, gateway_ip, user_id)

        driver.join_vpc(router_id, vxnet_id, user_id)

        driver.add_node(vxnet_id, l2vni, host, user_id)
        driver.remove_node(vxnet_id, host, user_id)

        driver.leave_vpc(router_id, vxnet_id, user_id)

        driver.delete_vxnet(vxnet_id, user_id)

        # cisco need roughly 10s to delete l3vni
        # need 10s interval when run this test repeatly
        driver.delete_vpc(router_id, user_id)
