import sys
sys.path.append('..')

from madt_lib.network import Network, Overlay

if len(sys.argv) != 2:
    print('Usage python ____ [ lab_path ]')
    sys.exit(1)

kt = Network('15.0.0.0/8')

routers = kt.generate_nodes('r', 3)
kt.create_subnet('core', routers)

for idx, router in enumerate(routers):
    n = kt.create_node('n'+str(idx+1))
    kt.create_subnet('net'+str(idx+1), (router, n))

    n.add_file('/me.txt', 'IM NODE #' + str(idx))

kt.create_overlay(Overlay.RIP, 'RIP', routers)
kt.render(sys.argv[1], verbose=True)

