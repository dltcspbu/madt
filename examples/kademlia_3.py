import sys
sys.path.append('..')

from madt_lib.network import Network

if len(sys.argv) != 2:
    print('Usage python ____ [ lab_path ]')
    sys.exit(1)


kt = Network('15.0.0.0/8')


nodes = kt.generate_nodes('n', 3, image='kademlia')
kt.create_subnet('net', nodes)

kt.configure(verbose=True)

for n in nodes[1:]:
    n.add_options(environment={'KADEMLIA_ARGS': nodes[0].get_ip()})

kt.render(sys.argv[1], verbose=True)



