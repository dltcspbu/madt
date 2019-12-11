import unittest
from madt_lib.network import Network
from madt_lib.node import Node


class TestNode(unittest.TestCase):
	main_net = '192.168.0.0/28'

	def setUp(self):
		self.network = Network(self.main_net, local=False, gateway=None, name='test_network')
		self.n = Node(name='test_node', network=self.network, image='madt/base')


class TestNodeInit(TestNode):
	def test_node_init(self):
		self.assertTrue('test_node' == self.n.name)

class TestNodeDockerConfig(TestNode):
	def test_docker_config(self):
		self.assertEqual('madt/base', self.n.docker_config()['image'])

class TestNodeSubnet(TestNode):
	def test_node_get_ip(self):
		node = Node(name='test_node_2', network=self.network, image='madt/base')
		self.n.connect(node=node, subnet_name='test')
		self.n.add_interface(subnet='test', ip='172.0.2.5')
		self.assertEqual('172.0.2.5', self.n.get_ip(subnet='test', as_str=True))



if __name__ == '__main__':
	unittest.main()