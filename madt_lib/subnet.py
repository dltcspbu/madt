from .utils import ceil_power_of_2
from .node import Node

class Subnet():
    """This class represents IP subnets of the network as well as
        virtual networks used in simulation.

    Attributes:
        name: A name of the subnet that'll leater be used as a name of the docker network.
        nodes: A list of nodes connected to the subnet.
        address: An ipaddress.IPv4Network, representing IP subnet.
        gateway: A default gateway to use for nodes in this subnet.
        docker_bridge: A reserved ip address.
    """

    def __init__(self, name, nodes, network, address=None, gateway=None):
        """Creates a new subnet of given network with given name.

        If gateway is not specified, it'll be chosen automatically from the routers,
        connected to this subnet.
        Note that subnets must be created through the parent network's methods,
        such as create_node or make_mesh rather than directly.

        Args:
            name: A name of the new subnet.
            nodes: A list of nodes to connect to the subnet.
            network: A parent Network of the subnet.
            gateway: An ip address with CIDR mask to use as default
                gateway for node it the subnet.
        """

        # this is used in node.get_nodes
        self.network = network

        self.name = name
        self.nodes = nodes
        self.address = address

        if gateway is None:
            router = next(filter(lambda n: n.type == Node.ROUTER, nodes), None)
            self.gateway = router
        else:
            self.gateway = gateway

        # TODO: GOD WHY
        self.docker_bridge = None

    def __str__(self):
        return self.name

    def set_address(self, address):
        self.address = address
        ip_iter = address.hosts()
        # another one for docker bridge
        self.docker_bridge = next(ip_iter)
        for node in self.nodes:
            node.add_interface(self, next(ip_iter))

    def size(self):
        return len(self.nodes)

    def _choose_and_set_address(self, address_pool):
        # desired_prefix = 32 - ceil_power_of_2(self.size() + 2)
        # another one for docker bridge
        desired_prefix = 32 - ceil_power_of_2(self.size() + 3)

        # sort, smaller nets first
        address_pool.sort(key=lambda n: -n.prefixlen)
        chosen_net = next(filter(lambda net: net.prefixlen <= desired_prefix, address_pool))
        address_pool.remove(chosen_net)

        if chosen_net.prefixlen == desired_prefix:
            self.set_address(chosen_net)
        else:
            new_net = next(chosen_net.subnets(new_prefix=desired_prefix))
            self.set_address(new_net)
            address_pool.extend(chosen_net.address_exclude(new_net))

    def docker_config(self):
        return {
            'subnet': str(self.address),
            'bridge': str(self.docker_bridge)
        }


    def find_router(self):
        for node in self.nodes:
            if node.type == node.ROUTER:
                return node
        return None

