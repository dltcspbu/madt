import sys
from argparse import ArgumentParser
from madt_lib.network import Network

sys.path.append('..')


def main():
    parser = ArgumentParser()
    parser.add_argument("lab_path", type=str, help='path to the lab directory')
    args = parser.parse_args()

    net = Network('15.0.0.0/8')

    nodes = net.generate_nodes('n', 3, image='kademlia')
    net.create_subnet('net', nodes)

    net.configure(verbose=True)

    for node in nodes[1:]:
        node.add_options(environment={'KADEMLIA_ARGS': nodes[0].get_ip()})

    net.render(args.lab_path, verbose=True)


if __name__ == "__main__":
    main()

