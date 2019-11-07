import os
from .node import Node


class Overlay:
    """A base class for dynamic routing Overlay"""

    RIP = 'RIP'
    OSPF = 'OSPF'
    BGP = 'BGP'
    protocol = None

    # this script is set as entrypoint for quagga docker image
    startup_path = '/etc/quagga/start.sh'

    zebra_conf_path = '/etc/quagga/zebra.conf'

    def __init__(self, name, nodes):
        """Creates new overlay.

        Given a name and list of nodes, this constructor will check if all
        nodes are not PC and will change their image to quagga and type to
        ROUTER instead. If there is a PC node in the list, an exception
        will be raised. An exception also will be raised if any of nodes
        already has this type of Overlay configured.
        Note that overlays must be created through the parent network's methods,
        such as create_overlay rather than directly.
        """
        self.name = name
        self.nodes = nodes

        for node in nodes:
            if node.type == Node.PC:
                raise Exception('Error: PC canot be a part of the overlay ({0})'.format(node.name))

            if self.protocol in node.quagga_settings:
                raise Exception('Overalys of each type must be unique for node')

            node.type = Node.ROUTER
            node.image = 'madt/quagga'

            node.quagga_settings[self.protocol] = {
                'overlay': self,
            }

    def __str__(self):
        return self.name

    def configure(self):
        for node in self.nodes:
            self.configure_node(node)

    def configure_node(self, node):
        # any connected subnet with other nodes in same overlay
        config = self._get_node_settings(node)

        config['networks'] = \
            [d.address for d in node.subnets() if any([n in self.nodes and n is not node for n in d.nodes])]

    def _get_node_settings(self, node):
        return node.quagga_settings[self.protocol]

    def _redistribution_config(self, node):
        return '\n'.join(
            ['redistribute ' + pr.lower() for pr, s in node.quagga_settings.items() if s['overlay'] is not self])

    def render(self):
        for node in self.nodes:
            self.create_files(node)

    # TODO: separate router class
    def create_files(self, node):
        print('render', self.name, 'on', node.name)
        if self.zebra_conf_path not in node.files:
            node.add_file(self.zebra_conf_path, 'hostname zebra\npassword zebra\nenable password zebra\nlog file /var/log/zebra/zebra.log\n')

        if self.startup_path in node.files:  # detach previous daemon and start new without detaching to keep
            node.files[self.startup_path] += '&\n ' + self.protocol.lower() + 'd start'  # container running
        else:
            node.add_file(self.startup_path, 'zebra start &\n' + self.protocol.lower() + 'd start')


class RIP_Overlay(Overlay):
    protocol = Overlay.RIP

    config_template = '''hostname ripd
password zebra
enable password zebra
router rip

{0}

redistribute connected

{1}

log file /var/log/zebra/ripd.log 
'''  # quagga fails to start, if line with log file is not at the bottom ????

    def create_files(self, node):
        super().create_files(node)
        node.add_file(
            '/etc/quagga/ripd.conf',
            self.config_template.format(
                '\n'.join(['network {0}'.format(n) for n in self._get_node_settings(node)['networks']]),
                self._redistribution_config(node)
            ))


class OSPF_Overlay(Overlay):
    protocol = Overlay.OSPF
    config_template = '''hostname ospfd
password zebra
enable password zebra
router ospf

{0}

redistribute connected

{1}

log file /var/log/zebra/ospfd.log
'''

    def __init__(self, name, nodes, weights={}, areas={}, default_weight=10):
        super().__init__(name, nodes)

    # TODO: areas & weights
    '''
    def configure_node(self, node):
        super().configure_node(self, node)

        node.quagga_settings[self.protocol]['weight'] = weights[node.name] \
            if node.name in weights else self.default_weight

    '''

    def create_files(self, node):
        super().create_files(node)
        node.add_file(
            '/etc/quagga/ospfd.conf',
            self.config_template.format(
                '\n'.join(['network {0} area 0.0.0.0'.format(n) for n in self._get_node_settings(node)['networks']]),
                self._redistribution_config(node)
            ))


class BGP_Overlay(Overlay):
    protocol = Overlay.BGP

    config_template = '''hostname bgpd
password zebra
enable password zebra
router bgp {0}
network {1}
{2}
log file /var/log/zebra/bgpd.log
debug bgp
debug bgp events
debug bgp filters
debug bgp fsm
debug bgp keepalives
debug bgp updates
'''

    def __init__(self, name, autonomous_systems):
        # autonomous_systems: [{nodes: [], gateways:[]}]
        self.autonomous_systems = autonomous_systems
        super().__init__(name, sum([list(AS['gateways']) for AS in autonomous_systems], []))

    def configure_node(self, node):
        config = self._get_node_settings(node)
        node_subnets = node.subnets()

        config['neighbors'] = []

        for other_node in self.nodes:
            other_AS = self._get_node_settings(other_node)['AS']
            if other_node is node or other_AS == config['AS']:
                continue

            common_ifc = next(filter(lambda ifc: ifc['subnet'] in node_subnets, other_node.interfaces), None)
            if common_ifc is None:
                continue

            config['neighbors'].append({
                'ip': common_ifc['ip'],
                'AS': other_AS,
            })

    def configure(self):
        for i, AS in enumerate(self.autonomous_systems):
            for node in AS['gateways']:
                self._get_node_settings(node)['AS'] = i + 1
                self._get_node_settings(node)['network'] = AS['subnet']

        super().configure()

    def create_files(self, node):
        super().create_files(node)
        settings = self._get_node_settings(node)

        node.add_file(
            '/etc/quagga/bgpd.conf',
            self.config_template.format(
                settings['AS'],
                settings['network'],
                '\n'.join(['neighbor {0} remote-as {1}'.format(n['ip'], n['AS']) for n in settings['neighbors']])))
