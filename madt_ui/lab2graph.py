import json

def from_config_old(config_file_name):

    with open(config_file_name) as config_file:
        lab_config = json.load(config_file)

    nodes = lab_config['nodes']
    edges = []

    networks = {}

    for name in nodes.keys():
        for network in nodes[name]['networks'].keys():

            if not network in networks:
                networks[network] = [name, ]
            else:
                for node in networks[network]:
                    edges.append({'source': name, 'target': node})

                networks[network].append(name)

    return {'nodes': nodes, 'edges': edges}


def from_config(config_file_name):

    with open(config_file_name) as config_file:
        lab_config = json.load(config_file)

    nodes = [{'data': {'id': name, 'router': config['isRouter']}, 'scratch': config} for name, config in lab_config['nodes'].items()]
    edges = []

    networks = {}
    possible_edges = {}

    for name in lab_config['nodes'].keys():
        for network in lab_config['nodes'][name]['networks'].keys():

            pseudo_node_id = '__' + network

            if network not in networks:
                networks[network] = name

            elif networks[network]:
                possible_edges[network] = {'data': {'source': networks[network], 'target': name}}
                networks[network] = False

            elif network in possible_edges:
                nodes.append({'data': {'id': pseudo_node_id, 'network': True, 'weight': 0}})

                edges.append({'data': {'source': possible_edges[network]['data']['source'], 'target': pseudo_node_id}})
                edges.append({'data': {'source': possible_edges[network]['data']['target'], 'target': pseudo_node_id}})
                edges.append({'data': {'source': name, 'target': pseudo_node_id}})

                possible_edges.pop(network)

            else:
                edges.append({'data': {'source': name, 'target': pseudo_node_id}})



    edges.extend(possible_edges.values())

    return {'nodes': nodes, 'edges': edges}



if __name__ == "__main__":
    print(from_config(input('lab.conf path? ')))