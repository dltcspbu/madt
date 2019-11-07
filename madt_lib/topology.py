import itertools


def _connect_pairs(pairs, subnet_prefix=None):

    if subnet_prefix is not None:
        return [
            pair[0].connect(pair[1], subnet_name=subnet_prefix + str(idx))
            for idx, pair in enumerate(pairs, 1)
        ]
    else:
        return [pair[0].connect(pair[1]) for pair in pairs]


def _prefix(subnet_prefix, idx):
    return subnet_prefix + str(idx) if subnet_prefix is not None else None



def chain(nodes, subnet_prefix=None):
    """Connects nodes in a chain network"""
    return _connect_pairs(zip(nodes, nodes[1:]))


def ring(nodes, subnet_prefix=None):
    """Connects nodes in a ring network"""
    return chain((nodes[-1], *nodes), subnet_prefix=subnet_prefix)


def star(center, nodes, subnet_prefix=None):
    """Connects nodes in a star network around center"""

    return [
        center.connect(node, subnet_name=_prefix(subnet_prefix, idx))
        for idx, node in enumerate(nodes, 1)
    ]


def grid(nodes, subnet_prefix=None):
    """Connects nodes in a mesh network"""

    n = len(nodes) ** 0.5 

    if int(n) != n:
        raise Exception("Mesh with n={} is not possible for {} nodes".format(n, len(nodes)))

    n = int(n)

    subnets = []

    for i in range(len(nodes)):
        # same row
        if (i // n) == ((i+1) // n):
            subnets.append(nodes[i].connect(nodes[i+1], subnet_name=_prefix(subnet_prefix, len(subnets) + 1)))

        # same columns
        if i + 4 < len(nodes):
            subnets.append(nodes[i].connect(nodes[i + 4], subnet_name=_prefix(subnet_prefix, len(subnets) + 1)))

        print('\n')

    return subnets


def mesh(nodes, subnet_prefix=None):
    """Connects nodes in a mesh network"""
    return _connect_pairs(itertools.combinations(nodes, 2), subnet_prefix)


def tree(nodes, n, subnet_prefix=None):
    """Connects nodes in a mesh network"""

    idx = 1
    subnets = []

    for node in nodes:
        if idx >= len(nodes):
            break

        for child in nodes[idx:idx+n]:
            subnets.append(node.connect(child, subnet_name=_prefix(subnet_prefix, len(subnets) + 1)))
            idx += n

    return subnets


def torus(nodes, subnet_prefix=None):
    """Connects nodes in a 2d-torus network"""
    n = 4

    if len(nodes) % n != 0:
        raise Exception("Torus with n={} is not possible for {} nodes".format(n, len(nodes)))

    subnets = []

    for i in range(nodes):

        # same row
        subnets.append(nodes[i].connect(nodes[(i+1) if i+1 < len(nodes) else 0],
                                        subnet_name=_prefix(subnet_prefix, len(subnets) + 1)))

        # same columns
        subnets.append(nodes[i].connect(nodes[(i+4) if i+4 < len(nodes) else (i - len(nodes) + 4)],
                                        subnet_name=_prefix(subnet_prefix, len(subnets) + 1)))

    return subnets


def fat_tree(network, nodes, k, node_prefix=None, subnet_prefix=None):
    """Connects nodes in a 3-level k-ary fat-tree network"""

    subnets = []

    if k % 2 != 0:
        raise Exception('k={} is not divisible by 2!'.format(k))

    node_prefix = '' if node_prefix is None else node_prefix
    subnet_prefix = '' if subnet_prefix is None else subnet_prefix

    core_switches = network.generate_nodes(node_prefix + 'core', (k/2) ** 2)
    nodes = [*core_switches,]

    idx = 0

    for i in range(k):

        pod_nodes = network.generate_nodes(node_prefix + 'pod{}_'.format(idx), k)
        nodes.append(pod_nodes)

        level_1 = pod_nodes[:2]
        level_2 = pod_nodes[2:]

        for j, n in enumerate(level_1):
            subnets.append(star(n, level_2, subnet_prefix=subnet_prefix + 'inra_pod{}_'.format(i)))
            subnets.append(star(n, core_switches[j*k/2:(j+1)*k/2], subnet_prefix=subnet_prefix + 'core_pod{}_'.format(i)))


        for n in level_2:
            subnets.append(star(n, nodes[idx, idx+k/2], subnet_prefix=subnet_prefix + 'server'.format(idx)))

    return nodes, subnets