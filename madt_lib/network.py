import os
import shutil
import itertools
import json
from ipaddress import *

from .node import Node
from .subnet import Subnet
from .overlay import Overlay, RIP_Overlay, OSPF_Overlay, BGP_Overlay

from .utils import ceil_power_of_2


class Network():
    """Base class for network definition.

    There should be only one global network in you lab that will represent the lab itself.
    Local networks, however, can be numerous and attached to a another local network as
    well as global network.
    Network methods shoul be directly used to populate it with nodes, subnets and overlays.

    Attributes:
        nodes: A list nodes of the network.
        subnets: A list of subnets of the network
        overlays: A list of overlays of the network
        local_networks: A list of local networks attached to the network
        BGP: A BGP dynamic routing overlay if configured for this network
        configured: A boolean indicating if IP addresses and routing
            protocols were conifgured in the network
        main_net: An ip address range that will be used in the network
        local: A boolean indicating if the network is local
        name: A string with the name of the network, that will be used as
            a prefix for networks nodes and subnets names.
        gateway: a default gateway for nodes in the local network.
    """

    def __init__(self, main_subnet, local=False, gateway=None, name='main'):
        """Creates a global network with a given range. To create a
            local network use appropriate method of another network"""

        self.nodes = []
        self.subnets = []
        self.overlays = []
        self.local_networks = []
        self.BGP = None

        self.configured = False

        if type(main_subnet) is str:
            main_subnet = ip_network(main_subnet)

        self.main_net = main_subnet
        self.local = local
        self.name = name
        self.gateway = gateway

    def create_node(self, name, **kwargs):
        """Creates a new node in the network.

        Creates a new node
        in the network with the given name. Name must be unique.
        In a local network the network's name will be used
        as a prefix. Any kwargs will be forwarded to the
        container.create from python docker API.

        Args:
            name: A string that will later be used as a container name.
            **kwargs: container creation options that will be forwarded to py-docker

        Returns:
            Created node.
        """

        if type(name) != str:
            raise TypeError('Node name must be str!')

        if name in [n.name for n in self.nodes]:
            raise Exception('Node name must be unique')

        if self.local:
            name = self.name + '_' + name

        new_node = Node(name, self,  **kwargs)
        self.nodes.append(new_node)
        return new_node

    def generate_nodes(self, prefix, num, **kwargs):
        """Creates several nodes in the network at once.

        Use this method to populate networks with large amount of nodes.
        Names for the nodes will be generated automatically from the prefix
        and index in generation.

        Args:
            prefix: A string to use in name generation.
            num: Number of nodes to generate.
            **kwargs: container creation options that will be forwarded to py-docker

        Returns:
            A list of created nodes.
        """

        if type(prefix) != str:
            raise TypeError('Prefix must be str!')

        if type(num) != int:
            raise TypeError('Num must be integer!')

        if num <= 0:
            raise ValueError('Num must be > 0!')

        return [self.create_node(prefix + str(i + 1), **kwargs) for i in range(num)]

    def create_subnet(self, name, nodes):
        """Connects nodes with a subnet.

        Args:
            name: a string that later will be used as a virtual network name.
            nodes: a list of nodes to be connected.

        Returns:
            Created subnet.
        """

        if name in [s.name for s in self.subnets]:
            raise Exception('Subnets name must be unique!')

        new_subnet = Subnet(name, nodes, self, gateway=self.gateway if self.gateway in nodes else None)
        self.subnets.append(new_subnet)
        return new_subnet

    def create_overlay(self, protocol, name, *args, **kwargs):
        """Creates a routing overlay in the network

        If protocol is RIP or OSPF *args and **kwargs will be
        forwarded to the corresponding constructor.
        If protocol is BGP, third argument must be a list
        describing the division of the network into Autonomous
        Systems (AS). Each element of this list should contain all the
        nodes in the corresponding AS, each node can only be in one AS.

        Args:
            protocol: one of Overlay.RIP, Overlay.OSPF or Overlay.BGP
            name: a name for new overlay

        Returns:
            Created overlay.
        """

        # return _add_overlay_fn[protocol](*args, **kwargs)
        if protocol == Overlay.RIP:
            new_overlay = RIP_Overlay(name, *args, **kwargs)
        elif protocol == Overlay.OSPF:
            new_overlay = OSPF_Overlay(name, *args, **kwargs)
        elif protocol == Overlay.BGP:
            if self.BGP is not None:
                raise Exception('Network BGP overlay must be unique')
            autonomous_systems = [{'nodes': nodes} for nodes in args[0]]
            for AS in autonomous_systems:
                AS['inner_subnets'] = []
                AS['border_subnets'] = []
                AS['gateways'] = set()

                for subnet in self.subnets:
                    inner_nodes = [n for n in subnet.nodes if n in AS['nodes']]

                    if len(inner_nodes) == len(subnet.nodes):
                        AS['inner_subnets'].append(subnet)

                    elif len(inner_nodes) == 0:
                        continue
                    else:
                        AS['gateways'].update(inner_nodes)
                        AS['border_subnets'].append(subnet)

            new_overlay = BGP_Overlay(name, autonomous_systems, **kwargs)
            self.BGP = new_overlay
        else:
            raise Exception("Wrong protocol!")

        self.overlays.append(new_overlay)
        return new_overlay

    def get_overlays(self, protocol=None):
        """Returns a networks overlays. If a protocol is given, returns
        corresponding overlays."""
        if protocol is None:
            return self.overlays
        else:
            return [o for o in self.overlays if o.protocol == protocol]

    def autonomous_systems(self):
        if self.BGP is not None:
            return self.BGP.autonomous_systems
        else:
            return []

    def create_local_network(self, gateway, main_subnet='192.168.0.0/16', name=None):
        """Creates a local network attached to this one.

        Args:
            gateway: a node to connect two networks.
                This node will be used to configure NAT.
            main_subnet: An ip range for the new network. Must be a
                valid ip range for private networks, i.e. 192.168.1.0/24
            name: A name for the new network. All networks in the lab must
                have unique names.

        Returns:
            Created network.
        """
        if type(main_subnet) is str:
            main_subnet = ip_network(main_subnet)

        if not main_subnet.is_private:
            raise Exception('Bad subnet for local network! Must be a private network.')

        if name in [n.name for n in self.local_networks]:
            raise Exception('Local networks names must be unique')

        if name is None:
            name = 'local{0}'.format(len(self.local_networks))

        new_net = Network(main_subnet, local=True, gateway=gateway, name=name)
        new_net.nodes.append(gateway)

        self.local_networks.append(new_net)
        return new_net

    def configure(self, verbose=False):
        """Distributes ip addresses and makes quagga configuration for routers"""

        self.subnets.sort(key=lambda d: d.size())

        # make ASs ip ranges
        if self.BGP is not None:
            subnets = list(self.main_net.subnets(ceil_power_of_2(len(self.autonomous_systems()) + 1)))
            print(subnets)
            transit_subnets = set()
        else:
            subnets = [self.main_net, ]
            transit_subnets = self.subnets

        for AS in self.autonomous_systems():
            subnet = subnets.pop()
            AS['subnet'] = subnet

            waiting_nets = [subnet, ]

            transit_subnets.update(AS['border_subnets'])

            for subnet in AS['inner_subnets']:
                subnet._choose_and_set_address(waiting_nets)

        waiting_nets = [subnets.pop(), ]
        for subnet in transit_subnets:
            subnet._choose_and_set_address(waiting_nets)

        for overlay in self.overlays:
            overlay.configure()

        if verbose:
            for subnet in self.subnets:
                print(subnet.name, subnet.address)

            for node in self.nodes:
                print(node.name, [ifc['ip'] for ifc in node.interfaces], node.quagga_settings, sep='\n\t')

        for net in self.local_networks:
            net.configure(verbose=verbose)

        self.configured = True

    def render(self, path, verbose=False):
        """Writes lab.json and actual quagga configuration files on a given path."""

        if not self.configured:
            self.configure(verbose=verbose)

        resolve_path = lambda *files: os.path.join(path, *files)

        if not self.local:
            try:
                shutil.rmtree(path)
            except FileNotFoundError:
                pass
            os.mkdir(path)

        for overlay in self.overlays:
            overlay.render()  # add quagga files to nodes

        nodes_config = {node.name: node.docker_config() for node in self.nodes}
        subnets_config = {subnet.name: subnet.docker_config() for subnet in self.subnets}

        if self.local:
            gateway_out_net = next(filter(lambda s: s not in self.subnets, self.gateway.subnets()), None)
            if gateway_out_net is None:
                raise Exception('Gateway node has no outgoing interfaces')
            nodes_config[self.gateway.name]['nat_net'] = gateway_out_net.name

            return (nodes_config, subnets_config)

        for net in self.local_networks:
            (net_nodes_config, net_subnets_config) = net.render(path, verbose=verbose)

            nodes_config.update(net_nodes_config)
            subnets_config.update(net_subnets_config)

        lab_conf = open(resolve_path('lab.json'), 'w')
        json.dump({'nodes': nodes_config, 'networks': subnets_config, 'subnet': str(self.main_net)}, lab_conf, indent=2)
