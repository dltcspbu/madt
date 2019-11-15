import sys
from argparse import ArgumentParser
from madt_lib.network import Network, Overlay

sys.path.append('..')


def main():
    parser = ArgumentParser()
    parser.add_argument("lab_path", type=str, help='path to the lab directory')
    args = parser.parse_args()

    net = Network('15.0.0.0/8')

    core = net.generate_nodes('core_', 3)
    routers = net.generate_nodes('r', 2)
    ospf_routers = net.generate_nodes('ospfr', 2)
    nodes = net.generate_nodes('n', 11, image='kademlia')

    net.make_mesh(core) # WAS IT DEPRECATED?

    # make subnets connecting each pair of nodes
    net.make_mesh((core[0], *routers)) # WAS IT DEPRECATED?

    net.create_subnet('ospf_1', (ospf_routers[0], core[2]))
    net.create_subnet('ospf_2', (ospf_routers[1], core[2]))

    net.create_subnet('lc1', (*nodes[:2], routers[0]))
    net.create_subnet('lc2', (*nodes[2:4], routers[1]))
    net.create_subnet('lc3', (*nodes[4:7], core[1]))
    net.create_subnet('lc4', (*nodes[7:9], ospf_routers[0]))
    net.create_subnet('lc5', (*nodes[9:], ospf_routers[1]))

    net.create_overlay(Overlay.RIP, 'RIP_1', (core[0], *routers))

    net.create_overlay(Overlay.OSPF, 'OSPF_1', (core[2], *ospf_routers))

    net.create_overlay(Overlay.BGP, 'big_boi', [
        [*nodes[:4], *routers, core[0]], [*nodes[4:7], core[1]], [*nodes[7:], *ospf_routers, core[2]]
    ])

    net.configure(verbose=True)

    for n in nodes[1:]:
        n.add_options(environment={'KADEMLIA_ARGS': nodes[0].get_ip()})

    net.render(args.lab_path, verbose=True)


if __name__ == "__main__":
    main()

