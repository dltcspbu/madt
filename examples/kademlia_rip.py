import sys
from argparse import ArgumentParser
from madt_lib.network import Network, Overlay

sys.path.append('..')


def main():
    parser = ArgumentParser()
    parser.add_argument("lab_path", type=str, help='path to the lab directory')
    args = parser.parse_args()

    main_net = Network('15.0.0.0/8')

    size = 3

    core = main_net.generate_nodes('core_', size)
    nodes = main_net.generate_nodes('n', size * 2, image='kademlia')

    main_net.create_subnet('core_net', core)

    for i in range(len(core)):
        main_net.create_subnet('radial_' + str(i), (core[i], nodes[2 * i], nodes[2 * i + 1]))

    main_net.create_overlay(Overlay.RIP, 'RIP_1', core)

    main_net.configure(verbose=True)

    for n in nodes[1:]:
        n.add_options(environment={'KADEMLIA_ARGS': nodes[0].get_ip()})

    main_net.render(args.lab_path, verbose=True)


if __name__ == "__main__":
    main()
