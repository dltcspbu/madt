import sys
from argparse import ArgumentParser
from madt_lib.network import Network, Overlay

sys.path.append('..')


def main():
    parser = ArgumentParser()
    parser.add_argument("lab_path", type=str, help='path to the lab directory')
    args = parser.parse_args()

    main_net = Network('15.0.0.0/8')

    core = main_net.generate_nodes('core_', 3)
    routers = main_net.generate_nodes('r', 2)
    ospf_routers = main_net.generate_nodes('ospfr', 2)
    nodes = main_net.generate_nodes('n', 11, image='kademlia')

    gateway = main_net.create_node('gateway')

    main_net.make_mesh(core) # WAS IT DEPRECATED?
    # make subnets connecting each pair of nodes
    main_net.make_mesh((core[0], *routers)) # WAS IT DEPRECATED?

    main_net.create_subnet('ospf_1', (ospf_routers[0], core[2]))
    main_net.create_subnet('ospf_2', (ospf_routers[1], core[2]))

    main_net.create_subnet('lc1', (*nodes[:2], routers[0]))
    main_net.create_subnet('lc2', (*nodes[2:4], routers[1], gateway))
    main_net.create_subnet('lc3', (*nodes[4:7], core[1]))
    main_net.create_subnet('lc4', (*nodes[7:9], ospf_routers[0]))
    main_net.create_subnet('lc5', (*nodes[9:], ospf_routers[1]))

    main_net.create_overlay(Overlay.RIP, 'RIP_1', (core[0], *routers))

    main_net.create_overlay(Overlay.OSPF, 'OSPF_1', (core[2], *ospf_routers))

    main_net.create_overlay(Overlay.BGP, 'big_boi', [
        [*nodes[:4], *routers, gateway, core[0]], [*nodes[4:7], core[1]], [*nodes[7:], *ospf_routers, core[2]]
    ])

    local_net = main_net.create_local_network(gateway)

    local_routers = local_net.generate_nodes('lan_router', 2)
    local_net.create_subnet('LAN0', (*local_routers, gateway))

    for idx, r in enumerate(local_routers):
        n = local_net.create_node('lan_node' + str(idx + 1), image='kademlia')
        local_net.create_subnet('LAN' + str(idx + 1), (n, r))
        nodes.append(n)

    local_net.create_overlay(Overlay.RIP, 'RIP_1', local_routers)

    main_net.configure(verbose=True)

    for n in nodes[1:]:
        n.add_options(environment={'KADEMLIA_ARGS': nodes[0].get_ip()})

    main_net.render(args.lab_path, verbose=True)


if __name__ == "__main__":
    main()