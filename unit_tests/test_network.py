import unittest
from madt_lib.network import Network

class TestNetworkInit(unittest.TestCase):

	main_net = '192.168.0.0/28'

	def setUp(self):
		self.network = Network(self.main_net, local=False, gateway=None, name='test_network')

	def test_main_net(self):
		self.assertEqual(self.network.main_net.exploded, self.main_net,
						'incorrect ip network')

	def test_local(self):
		self.assertEqual(self.network.local, False)

	def test_gateway(self):
		self.assertEqual(self.network.gateway, None)


class TestNetworkNodeManagement(unittest.TestCase):

	main_net = '192.168.0.0/28'

	def setUp(self):
		self.network = Network(self.main_net, local=False, gateway=None, name='test_network')

	def test_create_node(self):
		node_name = 'test_node'
		self.network.create_node(node_name)
		self.assertTrue(node_name in [node.name for node in self.network.nodes])


if __name__ == '__main__':
	unittest.main()
