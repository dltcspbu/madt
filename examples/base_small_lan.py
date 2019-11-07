import sys
sys.path.append('..')

from madt_lib.network import Network

if len(sys.argv) != 2:
    print('Usage python ____ [ lab_path ]')
    sys.exit(1)


main_net = Network('15.0.0.0/8')

nodes = main_net.generate_nodes('n', 3)
main_net.create_subnet('net', nodes)

local_net = main_net.create_local_network(nodes[0])

ln = local_net.create_node('l_n1')
local_net.create_subnet('LAN', (ln, nodes[0]))

main_net.configure(verbose=True)


main_net.render(sys.argv[1], verbose=True)
