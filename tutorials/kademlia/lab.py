from madt_lib.network import Network

def main():
    madt = Network('15.0.0.0/8')

    # create 20 nodes with names sensor_1, sensor_2 etc.
    nodes = madt.generate_nodes('sensor_', 20, image='madt/kademlia')
    # create a local network that will connect all those nodes
    madt.create_subnet('net', nodes)
    # distribute IP addresses
    madt.configure(verbose=True)

    for n in nodes[1:]:  # pass initial connection arguments to kademlia
        n.add_options(environment={'KADEMLIA_ARGS': nodes[0].get_ip()})
    # save lab
    madt.render('../../labs/kademlia', verbose=True)


if __name__ == "__main__":
    main()
