from madt_lib.network import Network, Overlay


def main():
    net = Network('15.0.0.0/8')

    # create network nodes that will represent client and server
    server = net.create_node('server', image='madt/docker_compose', enable_internet=True, privileged=True)
    clients = net.generate_nodes('client', 6, image='madt/pyget', environment={"SERVER": 'whoami.local'})

    with open('docker-compose.yml') as docker_compose_yml_file:
        server.add_dir('.', '/app')

    # create a local network that will connect all those nodes
    routers = net.generate_nodes('router', 3)
    net.create_subnet('subnet1', (routers[0], *clients[:3]))
    net.create_subnet('subnet2', (routers[1], *clients[3:]))
    net.create_subnet('subnet3', routers)
    net.create_subnet('subnet4', (routers[2], server))

    net.create_overlay(Overlay.RIP, 'RIP', routers)

    # distribute IP addresses
    net.configure(verbose=True)
    # pass server IP to the clients
    for client in clients:
        client.add_options(extra_hosts={'whoami.local': server.get_ip()})
    # save lab
    net.render('/home/demo/labs/compose', verbose=True)


if __name__ == "__main__":
    main()
