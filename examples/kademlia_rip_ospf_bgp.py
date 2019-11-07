import sys
sys.path.append('..')

from madt_lib.network import Network, Overlay

if len(sys.argv) != 2:
    print('Usage python ____ [ lab_path ]')
    sys.exit(1)


kt = Network('15.0.0.0/8')

core = kt.generate_nodes('core_', 3)
routers = kt.generate_nodes('r', 2)
ospf_routers = kt.generate_nodes('ospfr', 2)
nodes = kt.generate_nodes('n', 11, image='kademlia')


kt.make_mesh(core)
# make subnets connecting each pair of nodes
kt.make_mesh((core[0], *routers))

kt.create_subnet('ospf_1', (ospf_routers[0], core[2]))
kt.create_subnet('ospf_2', (ospf_routers[1], core[2]))

kt.create_subnet('lc1', (*nodes[:2], routers[0]))
kt.create_subnet('lc2', (*nodes[2:4], routers[1]))
kt.create_subnet('lc3', (*nodes[4:7], core[1]))
kt.create_subnet('lc4', (*nodes[7:9], ospf_routers[0]))
kt.create_subnet('lc5', (*nodes[9:], ospf_routers[1]))

kt.create_overlay(Overlay.RIP, 'RIP_1', (core[0], *routers))

kt.create_overlay(Overlay.OSPF, 'OSPF_1', (core[2], *ospf_routers))

kt.create_overlay(Overlay.BGP, 'big_boi', [
    [*nodes[:4], *routers, core[0]], [*nodes[4:7], core[1]], [*nodes[7:], *ospf_routers, core[2]]
])


kt.configure(verbose=True)

for n in nodes[1:]:
    n.add_options(environment={'KADEMLIA_ARGS': nodes[0].get_ip()})

kt.render(sys.argv[1], verbose=True)



