import sys
from argparse import ArgumentParser
from madt_lib.network import Network, Overlay
sys.path.append('..')

iterations = 2
children = 3
central_nodes = []
subnets = 1


def main():
    parser = ArgumentParser()
    parser.add_argument("lab_path", type=str, help='path to the lab directory')
    args = parser.parse_args()

    global subnets

    # Define network
    net = Network('15.0.0.0/8')

    # Create initial outer nodes and a subnet
    outer_nodes = [*net.generate_nodes('core_', children), ]
    net.create_subnet('core', outer_nodes)

    # Iteratively create other nodes
    for i in range(iterations):
        new_outer_nodes = []

        for node in outer_nodes:
            idx = outer_nodes.index(node) + 1

            new_nodes = net.generate_nodes('L{0}_N{1}_'.format(i, idx), children)
            net.create_subnet('L{0}_D{1}'.format(i, idx), (node, *new_nodes))
            subnets += 1

            new_outer_nodes.extend(new_nodes)

        central_nodes.extend(outer_nodes)
        outer_nodes = new_outer_nodes

    # OSPF - Open Shortest Path First
    net.create_overlay(Overlay.OSPF, 'OSPF', central_nodes)

    # Setup the node docker image
    for node in outer_nodes:
        node.image = 'kademlia'

    net.configure(verbose=True)

    for node in outer_nodes[1:]:
        node.add_options(environment={'KADEMLIA_ARGS': outer_nodes[0].get_ip()})

    net.render(args.lab_path, verbose=True)

    print('NET SIZE: ', len(central_nodes) + len(outer_nodes))
    print('SUBNETS: ', subnets)


if __name__ == "__main__":
    main()

