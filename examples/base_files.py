import sys
from argparse import ArgumentParser
from madt_lib.network import Network, Overlay

sys.path.append('..')


def main():
    parser = ArgumentParser()
    parser.add_argument("lab_path", type=str, help='path to the lab directory')
    args = parser.parse_args()

    net = Network('15.0.0.0/8')

    routers = net.generate_nodes('r', 3)
    net.create_subnet('core', routers)

    for idx, router in enumerate(routers):
        n = net.create_node('n' + str(idx + 1))
        net.create_subnet('net' + str(idx + 1), (router, n))

        n.add_file('/me.txt', 'IM NODE #' + str(idx))

    net.create_overlay(Overlay.RIP, 'RIP', routers)
    net.render(args.lab_path, verbose=True)


if __name__ == "__main__":
    main()

