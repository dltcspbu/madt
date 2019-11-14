import sys
from argparse import ArgumentParser
from madt_lib.network import Network

sys.path.append('..')


def main():
    parser = ArgumentParser()
    parser.add_argument("lab_path", type=str, help='path to the lab directory')
    args = parser.parse_args()

    net = Network('15.0.0.0/8')

    nodes = net.generate_nodes('n', 3)
    net.create_subnet('net', nodes)

    local_net = net.create_local_network(nodes[0])

    ln = local_net.create_node('l_n1')
    local_net.create_subnet('LAN', (ln, nodes[0]))

    net.configure(verbose=True)

    net.render(args.lab_path, verbose=True)


if __name__ == "__main__":
    main()
