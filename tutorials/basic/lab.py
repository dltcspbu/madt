from madt_lib.network import Network
kt = Network('15.0.0.0/8')
# create network nodes that will represent client and server
server = kt.create_node('server', image='madt/nginx')
client = kt.create_node('client', image='inutano/wget',
                        entrypoint='sh -c "while true; do wget -O - -T 3 $SERVER; sleep 1; done"')
# create a local network that will connect all those nodes
kt.create_subnet('net', (server, client))
# distribute IP addresses
kt.configure(verbose=True)
# pass server IP to the client
client.add_options(environment={'SERVER': server.get_ip()})
# save lab
kt.render('../../labs/basic_tutorial', verbose=True)
