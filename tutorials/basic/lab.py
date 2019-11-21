from madt_lib.network import Network


def main():
    net = Network('15.0.0.0/8')
    # create network nodes that will represent client and server
    server = net.create_node('server', image='madt/nginx')
    client = net.create_node('client', image='inutano/wget',
                            entrypoint='sh -c "while true; do wget -O - -T 3 $SERVER; sleep 1; done"')
    # create a local network that will connect all those nodes
    net.create_subnet('net', (server, client))
    # distribute IP addresses
    net.configure(verbose=True)
    # pass server IP to the client
    client.add_options(environment={'SERVER': server.get_ip()})
    # save lab
    net.render('../../labs/basic_tutorial', verbose=True)


if __name__ == "__main__":
    main()