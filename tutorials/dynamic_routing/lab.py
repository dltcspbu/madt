from madt_lib.network import Network, Overlay
kt = Network('15.0.0.0/8')

server = kt.create_node('server', image='madt/nginx')
clients = kt.generate_nodes('client', 6, image='inutano/wget',
                            entrypoint='sh -c "while true; do wget -O - -T 3 $SERVER; sleep 1; done"')

routers = kt.generate_nodes('router', 3)
kt.create_subnet('subnet1', (routers[0], *clients[:3]))
kt.create_subnet('subnet2', (routers[1], *clients[3:]))
kt.create_subnet('subnet3', routers)
kt.create_subnet('subnet4', (routers[2], server))

kt.create_overlay(Overlay.RIP, 'RIP', routers)

kt.configure(verbose=True)
for client in clients:
    client.add_options(environment={'SERVER': server.get_ip()})
kt.render('/home/demo/labs/dynamic_routing', verbose=True)
