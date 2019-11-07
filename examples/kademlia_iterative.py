import sys
sys.path.append('..')

from madt_lib.network import Network, Overlay

if len(sys.argv) != 2:
    print('Usage python ____ [ lab_path ]')
    sys.exit(1)


kt = Network('15.0.0.0/8')

iterations = 1
children = 10

# core = kt.create_node('core')

# outer_nodes = [core, ]
outer_nodes = [*kt.generate_nodes('core_', children), ]
kt.create_subnet('core', outer_nodes)
central_nodes = []

subnets = 1

for i in range(iterations):
    new_outer_nodes = []

    for node in outer_nodes:
        idx = outer_nodes.index(node) + 1

        new_nodes = kt.generate_nodes('L{0}_N{1}_'.format(i, idx), children)
        kt.create_subnet('L{0}_D{1}'.format(i, idx), (node, *new_nodes))
        subnets += 1

        new_outer_nodes.extend(new_nodes)

    central_nodes.extend(outer_nodes)
    outer_nodes = new_outer_nodes

kt.create_overlay(Overlay.OSPF, 'OSPF', central_nodes)

for node in outer_nodes:
    node.image = 'kademlia'

kt.configure(verbose=True)

for n in outer_nodes[1:]:
    n.add_options(environment={'KADEMLIA_ARGS': outer_nodes[0].get_ip()})

kt.render(sys.argv[1], verbose=True)

print('NET SIZE: ', len(central_nodes) + len(outer_nodes))
print('SBUNETS: ', subnets)

