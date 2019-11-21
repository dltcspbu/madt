from madt_lib.network import Network, Overlay


def main():
    madt = Network('15.0.0.0/8')
    # create network nodes that will represent client and server
    server = madt.create_node('server', image='madt/nginx')
    clients = madt.generate_nodes('client', 6, image='madt/pyget')
    # create a local network that will connect all those nodes
    routers = madt.generate_nodes('router', 3)
    madt.create_subnet('subnet1', (routers[0], *clients[:3]))
    madt.create_subnet('subnet2', (routers[1], *clients[3:]))
    madt.create_subnet('subnet3', routers)
    madt.create_subnet('subnet4', (routers[2], server))

    madt.create_overlay(Overlay.RIP, 'RIP', routers)

    # distribute IP addresses
    madt.configure(verbose=True)
    # pass server IP to the clients
    for client in clients:
        client.add_options(environment={'SERVER': server.get_ip()})
    # save lab
    madt.render('../../labs/monitoring', verbose=True)


if __name__ == "__main__":
    main()
