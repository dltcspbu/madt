import io
import os
from .utils import DynamicTar

class Node():
    """This class represents nodes of the network: both routers and PCs.

    Attributes:
        name: A string that'll later be used as a container name.
        image: An image that'll later be used to create a container
        type: Either Node.PC or Node.ROUTER. Only router can be a part of Overlay.
        interfaces: A list of dicts representing network connection of the Node.
            Each dictionary has two keys: 'ip' and 'subnet', with corresponding values.
            The list is empty until global network's configure() method is called.
        quagga_settings: A dict with raw data that'll be rendered into quaggga
            configuration files when global network's render() method is called.
            Thsi attribute is also empty until global network's configure()
            method is called.
        enable_internet: A boolean indicating if node/container needs to be able to
            communicate with the world outside the model.
        docker_options: kwargs dictionary that'll be redirected to the
            py-docker containers.create API
    """

    PC = 'PC'
    ROUTER = 'ROUTER'
    GATEWAY = 'GATEWAY'

    def __str__(self):
        return self.name

    def __init__(self, name, network, image='madt/base', enable_internet=False, tc_options={}, files={}, **kwargs):
        """Creates new node with a given name.

        Note that nodes must be created through the parent network's methods,
        such as generate_nodes or create node rather than directly. Any kwargs
        passed to those methods will be forwarded to this constructor.

        Args:
            name: A name of the new node. Must be unique across parent network.
            image: A name of docker image to use when starting this node
            enable_internet: A boolean indicating if node/container needs to be able to
                communicate with the world outside the model.
            tc_options: TC policies to apply to container on start, format is the same as with API
            files: dict where keys are deployment paths, and values are strings/files to be deployed
            **kwargs: options that'll be redirected to the
                py-docker containers.create API
        """
        self.network = network

        self.name = name
        self.image = image
        self.type = self.PC if image != 'madt/base' else None
        self.interfaces = []

        self.quagga_settings = {}

        self.enable_internet = enable_internet

        self.docker_options = dict(kwargs)
        self.tc_options = tc_options.copy()
        self.files = files.copy()
        self.directories = {}


    def get_options(self):
        return self.docker_options

    def add_options(self, **kwargs):
        self.docker_options.update(kwargs)

    def add_interface(self, subnet, ip):
        self.interfaces.append({'subnet': subnet, 'ip': ip})

    def neighbors(self):
        """Returns a list of all nodes that have direct network
            connection with this one."""
        neighbors = []
        for ifc in self.interfaces:
            neighbors += ifc['subnet'].nodes

    def subnets(self):
        """Returns a list of all subnets node connected to."""
        return [ifc['subnet'] for ifc in self.interfaces]

    def connect(self, node, subnet_name=None):
        """Connects a node to another with a subnet"""
        net = self.network if self.type != self.GATEWAY else node.network

        return net.create_subnet(subnet_name or '{}_{}'.format(self.name, node.name), (self, node))

    def add_file(self, path, file):
        """Adds a file to node files.

        Args:
            path: path (with name) in the container where file will be placed on start
            file: string or file-like object that later will be saved in the container
        """
        print('adding file ', path, 'on', self.name)
        if path in self.files:
            raise FileExistsError(path)

        if isinstance(file, io.IOBase):
            self.files[path] = file.read()
        else:
            self.files[path] = file


    def add_dir(self, source_path, dist_path):
        """Adds a file to node files.

        Args:
            source_path: directory absolute path
            dist_path: path (with name) in the container where to place directory
        """
        print('adding dir {} on {} as {}'.format(source_path, self.name, dist_path))
        if dist_path in self.directories:
            raise FileExistsError(dist_path)

        tar = DynamicTar.from_dir(source_path, dir_arcname=os.path.basename(dist_path))

        self.directories[dist_path] = tar.to_base64()


    def docker_config(self):
        """Creates a minifyed json-serializable node representation t
            hat will be stored in lab directory and used to start it 
            later.
        """

        return {
            'image': self.image,
            'isRouter': self.type in (self.ROUTER, self.GATEWAY),
            'networks': {ifc['subnet'].name: str(ifc['ip'])+'/'+str(ifc['subnet'].address.prefixlen) for ifc in self.interfaces},
            'options': self.docker_options,
            'enableInternet': self.enable_internet,
            'routes': self._get_routes(),
            'tc_options': self.tc_options,
            'files': self.files,
            'directories': self.directories
        }

    def get_ip(self, subnet=None, as_str=True):
        """Returns one of the nodes ip addresses

        If subnet is specified, this method will return ip address of
        the corresponding connection.

        Args:
            subnet: a subnet to get ip address from.
            as_str: a boolean specifying desired result type.

        Returns:
            If as_str is true will return ip address as a string.
            If not, then result will be instance of ipaddress.IPv4Address
        """

        if not self.interfaces:
            raise Exception('Node has no interfaces!')

        if subnet is None:
            ret = self.interfaces[0]['ip']
        else:
            ifc = next(filter(lambda ifc: ifc['subnet'] is subnet, self.interfaces), None)

            if ifc is None:
                raise Exception('Node does not have interfaces in this subnet!')

            ret = ifc['ip']

        return ret if not as_str else str(ret)

    '''
                Short essay: dynamic routers and local networks gateways
    
                router?
                N               Y
    gate?   N   just            also default 
                find a          route to nearby router,
                router          which hopefully never will be used

            Y   default to      A: Overlay is on the outside: default will never be used,
                main net           route to the local network still will be useful
                and local       B: Overlay is in the inside: default for outside traffic,
                network route      and the inside route will be less specific than any of the
                to a router        dynamic routes, so it won't interfere with them (hopefully)  
                inside             
    '''
    def _get_routes(self):
        subnets = self.subnets()

        ret = {}

        for s in subnets:
            key = str(s.network.main_net) if s.network.local else 'default'

            if key in ret:
                continue

            router = s.find_router()
            if router is not None:
                ret[key] = router.get_ip(subnet=s)

        for subnet in subnets:
            if subnet.gateway and subnet.gateway is not self:
                ret['default'] = subnet.gateway.get_ip(subnet=subnet)

        if len(ret) == 1:
            return {'default': next(iter(ret.values()))}

        return None if not ret else ret
