from madt_lib.network import Network, Overlay
kt = Network('15.0.0.0/8')
# create network nodes that will represent client and server
server = kt.create_node('server', image='madt/nginx')
clients = kt.generate_nodes('client', 6, image='madt/pyget')
# create a local network that will connect all those nodes
routers = kt.generate_nodes('router', 3)
kt.create_subnet('subnet1', (routers[0], *clients[:3]))
kt.create_subnet('subnet2', (routers[1], *clients[3:]))
kt.create_subnet('subnet3', routers)
kt.create_subnet('subnet4', (routers[2], server))

kt.create_overlay(Overlay.RIP, 'RIP', routers)

# distribute IP addresses
kt.configure(verbose=True)
# pass server IP to the clients
for client in clients:
    client.add_options(environment={'SERVER': server.get_ip()})
# save lab
kt.render('/home/demo/labs/monitoring', verbose=True)
