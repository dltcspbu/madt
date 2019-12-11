import unittest
from madt_lib.network import Network
from madt_lib.overlay import Overlay


class TestNetwork(unittest.TestCase):
	main_net = '192.168.0.0/28'

	def setUp(self):
		self.network = Network(self.main_net, local=False, gateway=None, name='test_network')


class TestNetworkInit(TestNetwork):
	def test_main_net(self):
		self.assertEqual(self.network.main_net.exploded, self.main_net,
						'incorrect ip network')

	def test_local(self):
		self.assertEqual(self.network.local, False)

	def test_gateway(self):
		self.assertEqual(self.network.gateway, None)


class TestNetworkNodeManagement(TestNetwork):
	def test_create_node(self):
		node_name = 'test_node'
		self.network.create_node(node_name)
		self.assertTrue(node_name in [node.name for node in self.network.nodes])

		with self.assertRaises(TypeError):
			self.network.create_node(0)

		with self.assertRaises(Exception):
			self.network.create_node(node_name)

	def test_local_naming(self):
		test_net = Network(self.main_net, local=True, gateway=None, name='test_network')
		test_net.create_node('test_node')
		self.assertTrue(test_net.name + '_' + 'test_node' in [node.name for node in test_net.nodes])

	def test_generate_nodes(self):
		self.network.generate_nodes(prefix='test', num=10)
		for i in range(0, 10):
			self.assertTrue('test' + str(i+1) in [node.name for node in self.network.nodes])

		with self.assertRaises(TypeError):
			self.network.generate_nodes(prefix=0, num=10)

		with self.assertRaises(TypeError):
			self.network.generate_nodes(prefix='test1', num='test_test')

		with self.assertRaises(ValueError):
			self.network.generate_nodes(prefix='test2', num=-10)

	def test_create_subnet(self):
		node1 = self.network.create_node("node1_for_subnet")
		node2 = self.network.create_node("node2_for_subnet")
		subnet = self.network.create_subnet("test_subnet", [node1, node2])

		self.assertTrue(subnet in self.network.subnets)

		with self.assertRaises(TypeError):
			self.network.create_subnet(0, [node1, node2])

		with self.assertRaises(Exception):
			self.network.create_subnet("test_subnet", [node1, node2])


class TestNetworkOverlays(TestNetwork):
	def test_create_overlay(self):
		with self.assertRaises(TypeError):
			self.network.create_overlay(protocol=0, name='test_integer_protocol')

		with self.assertRaises(TypeError):
			self.network.create_overlay(protocol=Overlay.RIP, name=0)

		with self.assertRaises(Exception):
			self.network.create_overlay(protocol='Best_protocol', name='test_wrong_protocol')

		nodes_rip = self.network.generate_nodes(prefix='rip', num=10)
		self.network.create_overlay(protocol=Overlay.RIP, name='test_RIP', nodes=nodes_rip)
		self.assertTrue(Overlay.RIP in [overlay.protocol for overlay in self.network.overlays])

		nodes_bgp = self.network.generate_nodes(prefix='bgp', num=10)
		nodes_bgp2 = self.network.generate_nodes(prefix='bgp2', num=10)
		self.network.create_overlay(Overlay.BGP, 'test_BGP', [nodes_bgp, nodes_bgp2])
		self.assertTrue(Overlay.BGP in [overlay.protocol for overlay in self.network.overlays])

		nodes_ospf = self.network.generate_nodes(prefix='ospf', num=10)
		self.network.create_overlay(protocol=Overlay.OSPF, name='test_OSPF', nodes=nodes_ospf)
		self.assertTrue(Overlay.OSPF in [overlay.protocol for overlay in self.network.overlays])

	def test_get_overlays(self):
		nodes_rip = self.network.generate_nodes(prefix='rip', num=10)
		self.network.create_overlay(protocol=Overlay.RIP, name='test_RIP', nodes=nodes_rip)
		self.assertTrue(Overlay.RIP in [overlay.protocol for overlay in self.network.get_overlays(protocol=Overlay.RIP)])

class TestNetworkLocalNetwork(TestNetwork):
	def test_create_local_network(self):
		with self.assertRaises(Exception):
			self.network.create_local_network(gateway=None, main_subnet=0)

		self.network.create_local_network(gateway=None, name='test_local_network')
		self.assertTrue('test_local_network' in [network.name for network in self.network.local_networks])

class TestNetworkConfigure(TestNetwork):
	def test_configure(self):
		nodes=self.network.generate_nodes(prefix='test', num=10)
		self.network.create_overlay(protocol=Overlay.RIP, name='rip', nodes=nodes)
		self.network.configure(verbose=True)
		self.assertTrue(self.network.configured)


if __name__ == '__main__':
	unittest.main()
