import docker
import os
from random import choice, shuffle
import time
import subprocess
import socket
import hashlib
from contextlib import closing
import tempfile
import sys
import shutil
import socket

from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend as crypto_default_backend

from .. import utils

port_range = list(range(9100, 9200))
try:
    server_ip = os.environ['MADT_SERVER_ADDRESS']
except KeyError:
    server_ip = socket.gethostname()

def format_entrypoint(ep):
    if type(ep) is str:
        return ep
    return ' ' + ' '.join(['"{}"'.format(cmd) for cmd in ep])

def find_free_port():
    shuffle(port_range)

    for port in port_range:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.settimeout(2)
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port

    raise Exception("No free ports in range!")


def my_hash(s, length=16):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()[:length]


def get_docker_api(host_config):

    if host_config['protocol'] == 'tcp':
        url = '{0}://localhost:{1}'.format(host_config['protocol'], host_config['docker_port'])
    else:
        url = '{0}://{1}'.format(host_config['protocol'], host_config['address'])

    return docker.DockerClient(base_url=url)


def split_lab(lab_config, host_configs):

    nodes = list(lab_config['nodes'].keys())
    networks = list(lab_config['networks'].keys())

    if len(host_configs) == 1:
        print('Only one node, no need for kahypar')

        docker_nets = networks
        wireguard_nets = []

        host_config = next(iter(host_configs.values()))

        host_config['nodes'] = nodes
        host_config['docker_networks'] = networks

        return docker_nets, wireguard_nets

    # convert lab to hMetis format
    graph_repr = ['{} {}'.format(len(lab_config['networks']), len(lab_config['nodes'])),
                  *['' for n in networks]]

    fix_file = []

    # {network name: indexes of all nodes in the nerwork}
    reverse_net_map = {net: [] for net in networks}

    for node_idx, node in enumerate(nodes):
        for net in lab_config['nodes'][node]['networks']:
            graph_repr[networks.index(net) + 1] += str(node_idx+1) + ' '
            reverse_net_map[net].append(node_idx)

        fix_file.append('0' if lab_config['nodes'][node]['isRouter'] else '-1')

    graph_repr = '\n'.join(graph_repr)
    fix_file = '\n'.join(fix_file)

    with tempfile.TemporaryDirectory() as tmp_dir:

        preset = '/kahypar/config/cut_kahypar_mf_jea19.ini'
        max_imbalance = 0.03

        tmp_filename = os.path.join(tmp_dir, 'in.graph')
        tmp_fix_filename = os.path.join(tmp_dir, 'fix_file')

        with open(tmp_filename, 'w') as tmp_file:
            tmp_file.write(graph_repr)

        with open(tmp_fix_filename, 'w') as tmp_file:
            tmp_file.write(fix_file)

        ret = subprocess.run(
            'kahypar -h {0} -k {1} -e {2} -o cut -m direct -f {4} -p {3} && rm {0} && rm {4}'.format(tmp_filename,
                                                                                                     len(host_configs),
                                                                                                     max_imbalance,
                                                                                                     preset,
                                                                                                     tmp_fix_filename),
            shell=True,
            capture_output=True)

        if ret.returncode != 0:
            raise Exception("Error while using KaHyPar: \n" + ret.stdout.decode() + '/n' + ret.stderr.decode())

        try:
            ret_filename = os.path.join(tmp_dir, os.listdir(tmp_dir)[0])
        except:
            raise Exception("Error: KaHYPar did not create any files")

        print('\noutfile:', ret_filename, '\n')

        with open(ret_filename) as ret_file:
            raw_partition = [int(line) for line in ret_file.read().split('\n')[:-1]]


    host_configs_list = list(host_configs.values())

    for host_config in host_configs_list:
        host_config['docker_networks'] = []
        host_config['nodes'] = []

    for node_idx, part_idx in enumerate(raw_partition):
        host_configs_list[part_idx]['nodes'].append(nodes[node_idx])

    docker_nets = []
    wireguard_nets = []

    print('reverse map', reverse_net_map, sep='\n')
    print('raw partition', raw_partition, sep='\n')

    for net in networks:  # assigned partitions are not the same for all nodes

        partition = raw_partition[reverse_net_map[net][0]]

        print(net, [(raw_partition[node_idx], partition) for node_idx in reverse_net_map[net]], sep='\n')

        if all([raw_partition[node_idx] == partition for node_idx in reverse_net_map[net]]):
            host_configs_list[partition]['docker_networks'].append(net)
            docker_nets.append(net)
        else:
            wireguard_nets.append(net)

    print('[ lab partition ]\n[ docker nets ]\n', *docker_nets, '\n[ vpn nets ]\n', *wireguard_nets)

    return docker_nets, wireguard_nets


def ssh_exec(cmd, host_config):
    print('\n[ ssh exec ]', cmd)
    ret = subprocess.run("ssh -p {} root@localhost {}".format(host_config['ssh_port'], cmd),
                         stdout=subprocess.PIPE, universal_newlines=True, stderr=subprocess.STDOUT,
                         shell=True)

    print('[ ssh exec ] status:  ', ret.returncode, '\n', ret.stdout, sep='')

    return ret.returncode, ret.stdout


def write_trough_ssh(text, path, host_config):
    print('\n[ ssh write ]', path, 'on', host_config['address'])

    cmd = "echo '{0}' | ssh -p {2} -T root@localhost \"cat > {1}\"".format(
            text,
            path,
            host_config['ssh_port'])

    # print(cmd)

    ret = subprocess.run(cmd,
        stdout=subprocess.PIPE,
        universal_newlines=True,
        stderr=subprocess.STDOUT,
        shell=True)

    print('[ ssh write ] status:  ', ret.returncode, '\n', ret.stdout, sep='')

    return ret.returncode, ret.stdout


def forward_socket(prefix, local_socket_path, remote_socket_path, host_configs):
    # bad decision, all socket management should be in one place
    cmd = 'until [ -e "{}" ]; do sleep 3; done;'.format(local_socket_path)

    print('\n[ fwd ]', local_socket_path, 'to', list(host_configs.keys()))

    # no python ssh clients have remote (or reverse) ssh tunnel support
    for host_name, host_config in host_configs.items():
        cmd += 'ssh -p {0} localhost mkdir -p {1};\n'.format(host_config['ssh_port'],
                                                        os.path.split(remote_socket_path)[0])
        cmd += 'ssh -f -N -p {0} -R {1}:{2} localhost;\n'.format(host_config['ssh_port'],
                                                        local_socket_path, remote_socket_path)
        cmd += 'pgrep -f -n "ssh -f -N -p {0}" > /var/run/ssh.{1}_{2}.pid;\n'.format(
            host_config['ssh_port'],
            prefix,
            host_name,
        )

    print('\n\n[ ssh fwd ]', cmd, sep='\n')

    process = subprocess.Popen("sh -c '{}' > /ssh.log 2>&1 &".format(cmd), shell=True)

    return process.pid


def generate_key_pair():
    key = rsa.generate_private_key(
        backend=crypto_default_backend(),
        public_exponent=65537,
        key_size=4096)

    private_key = key.private_bytes(
        crypto_serialization.Encoding.PEM,
        crypto_serialization.PrivateFormat.PKCS8,
        crypto_serialization.NoEncryption())

    public_key = key.public_key().public_bytes(
        crypto_serialization.Encoding.PEM,
        crypto_serialization.PublicFormat.PKCS1)

    return private_key.decode(), public_key.decode()


node_tinc_config_template = """
Name = {name}
Forwarding = kernel
StrictSubnets = yes
AddressFamily = ipv4
Interface = tun{idx}
LocalDiscovery = yes
ConnectTo = madt_server
"""

# not really node tinc-up, since it'l be executed on host
#
node_tinc_up_tempalte = """#!/bin/sh
pid=$(/usr/local/bin/docker inspect -f "{{{{.State.Pid}}}}" "{c_id}");
if [ ! -e /var/run/netns/$pid ]; then
    echo "No netns, making one rn"
    ln -s /proc/$pid/ns/net /var/run/netns/$pid
fi
ip link set tun{idx} netns $pid;
ip -n $pid address add dev tun{idx} {ip};
ip -n $pid link set tun{idx} up
"""


def setup_vpn(vpn_nets, lab_config, prefix):
    server_private_key, server_public_key = generate_key_pair()

    for idx, net in enumerate(vpn_nets):
        net_config = lab_config['networks'][net]
        server_port = find_free_port()

        bridge_ip = net_config['bridge'] + '/' + net_config['subnet'].split('/')[1]

        server_host_config_on_nodes = "Address = {0}\nSubnet = {1}\nPort={2}\n\n{3}".format(
            server_ip,
            lab_config['subnet'],
            server_port,
            server_public_key
        )

        server_host_config_on_routers = "Address = {0}\nSubnet = {1}\nPort={2}\n\n{3}".format(
            server_ip,
            net_config['subnet'],
            server_port,
            server_public_key
        )

        server_host_config_on_server = "Address = {0}\nSubnet = {1}\nPort={2}\n\n{3}".format(
            server_ip,
            bridge_ip,
            server_port,
            server_public_key
        )

        net_config['server_host_config_on_nodes'] = server_host_config_on_nodes
        net_config['server_host_config_on_routers'] = server_host_config_on_routers

        server_tinc_config = "Name = madt_server\nMode = hub\nStrictSubnets = yes\nAddressFamily = ipv4\nInterface = tun{0}\nLocalDiscovery = yes\nPort={1}"\
            .format(idx, server_port)

        server_tinc_up = 'ip addr add {0} dev tun{1}'.format(
            bridge_ip,
            idx
        )

        node_configs = {}

        for node, node_config in lab_config['nodes'].items():
            if net not in node_config['networks']:
                continue

            if 'keys' not in node_config:
                node_private_key, node_public_key = generate_key_pair()
                node_config['keys'] = (node_private_key, node_public_key)
            else:
                node_private_key, node_public_key = node_config['keys']

            node_ip = node_config['networks'][net] # ip with subnet's prefixlen

            if 'tinc' not in node_config:
                node_config['tinc'] = {}

            node_host_config = 'Subnet = {0}\nPort = 0\n\n'.format(node_ip.split('/')[0] + '/32') + node_public_key
            '''# Port 0 i.e bind any free port
            if not node_config['isRouter']:
                node_host_config = 'Subnet = {0}\nPort = 0\n\n'.format(node_ip.split('/')[0] + '/32') + node_public_key
            else:
                node_host_config = 'Subnet = {0}\nPort = 0\n\n'.format(lab_config['subnet'])'''
            node_configs[node] = node_host_config

            # all the other configs need interface idx that'll be known only on the runtime
            node_config['tinc'][net] = node_host_config

        config_root = '/etc/tinc/' + prefix + net

        print('making', net, 'tinc dir')

        try:
            shutil.rmtree(config_root)
        except FileNotFoundError:
            pass
        os.makedirs(os.path.join(config_root, 'hosts'))

        print('tinc dir ready, writing files')

        with open(os.path.join(config_root, 'tinc.conf'), 'w') as f:
            f.write(server_tinc_config)

        with open(os.path.join(config_root, 'tinc-up'), 'w') as f:
            f.write(server_tinc_up)

        with open(os.path.join(config_root, 'rsa_key.priv'), 'w') as f:
            f.write(server_private_key)

        print('now host files')

        with open(os.path.join(config_root, 'hosts', 'madt_server'), 'w') as f:
            f.write(server_host_config_on_server)

        for name, config in node_configs.items():
            with open(os.path.join(config_root, 'hosts', name), 'w') as f:
                f.write(config)

        print('files ready')

        ret = subprocess.run('chmod +x /etc/tinc/{0}/tinc-up && tincd -n {0}'.format(prefix+net), capture_output=True, shell=True)

        print('[ tinc out ]', ret.stdout.decode(), ret.stderr.decode(), sep='\n')

        # return ret.


def start_lab(lab_path, prefix, host_configs, image_prefix='', timeout=3 * 60, poll_interval=10, default_tc_options={}):
    lab_config = utils.load_lab_config(lab_path)
    lab_name = os.path.basename(lab_path)

    ret = {}

    print('[ starting ]')

    # this will also set 'nodes' in hosts configs
    docker_nets, wireguard_nets = split_lab(lab_config, host_configs)

    # socket management
    try:
        # in-container case
        socket_dir = os.environ['MADT_LABS_SOCKETS_DIR']
    except KeyError:
        socket_dir = os.path.abspath('./sockets/')
    socket_dir = os.path.join(socket_dir, lab_name)
    socket_path = os.path.join(socket_dir, 'lab.sock')  # /sockets/{{ lab_name }}/lab.sock

    try:
        shutil.rmtree(socket_dir)
    except Exception as e:
        print(e)
        pass
    os.mkdir(socket_dir)

    setup_vpn(wireguard_nets, lab_config, prefix)
    print('vpn setup done')

    tc_options_cache = {}
    killed_routers = []
    for host, host_config in host_configs.items():
        containers = []
        dc = get_docker_api(host_config)

        host_docker_networks = {}
        print('creating networks on {}...'.format(host), flush=True)

        # tunX names must be unique across all namespaces
        tun_i = 0

        for network in host_config['docker_networks']:
            print(network, flush=True)

            '''config = lab_config['networks'][network]
            masklen = config['subnet'].split('/')[1]

            docker_networks[network] = dc.networks.create(
                prefix + network,
                ipam=docker.types.IPAMConfig(driver='mini',
                                             options={
                                                 'com.github.mini.cidr_mask_length': masklen}
                                             ))'''
            host_docker_networks[network] = dc.networks.create(prefix + network, driver='bridge')
        print('...done', flush=True)

        image_cache = {}
        tcwrap_config = ''

        print('setting up containers on {}...'.format(host), flush=True)
        for node in host_config['nodes']:
            config = lab_config['nodes'][node]
            print(node, flush=True, end=' ')

            image_name = image_prefix + '/' + config['image'] if image_prefix else config['image']

            if image_name in image_cache:
                image = image_cache[image_name]
            else:

                try:
                    image = dc.images.get(image_name)
                except docker.errors.ImageNotFound:
                    if ':' in image_name:
                        image_name, tag = image_name.split(':', maxsplit=1)
                    else:
                        tag = 'latest'

                    image = dc.images.pull(image_name, tag=tag)

                image_cache[image_name] = image

            create_kwargs = {
                'environment': {},
                **config['options'],
                'image': image,
                'hostname': node,
                'name': prefix + node,
                'volumes': {socket_dir: {'bind': '/lab', 'mode': 'rw'}},
                'detach': True,
                'cap_add': ["NET_ADMIN"],
                'version': dc.api._version,
            }

            enable_internet = config['enableInternet']
            has_docker = any([n in docker_nets for n in config['networks'].keys()])
            vpn_gateway = None

            first_network = None

            if not config['isRouter']:
                # -e - exist anything, -f exist and regular file, -S exist and socket
                new_entrypoint = "sh -c 'until [ -e '/lab/lab.sock' ]; do sleep 3; done;"

                has_custom_entrypoint = 'entrypoint' in config['options']
                has_custom_cmd = 'command' in config['options']

                if image.attrs['Config']['Entrypoint']:
                    original_entrypoint = image.attrs['Config']['Entrypoint']
                    for i, cmd in enumerate(original_entrypoint[:-1]):
                        # TODO: fix this
                        # this is ugly, we need to find another way,
                        # but docker don't seem to like multiple *sh -c in entrypoint for some reason
                        if cmd[-2:] in ['bash', 'ash', 'sh', '/bin/bash',
                                        '/bin/ash', '/bin/sh'] and \
                                original_entrypoint[i + 1] == '-c':
                            original_entrypoint.pop(i)
                            original_entrypoint.pop(i)
                    if not has_custom_entrypoint:
                        new_entrypoint += format_entrypoint(original_entrypoint)
                if image.attrs['Config']['Cmd'] and not (has_custom_cmd or has_custom_entrypoint):
                    new_entrypoint += format_entrypoint(image.attrs['Config']['Cmd'])
                if has_custom_entrypoint:
                    new_entrypoint += format_entrypoint(config['options']['entrypoint'])
                if has_custom_cmd:
                    new_entrypoint += format_entrypoint(config['options']['command'])

                new_entrypoint += "'"

                print('[ EP ]', new_entrypoint, sep='\n')

                create_kwargs['entrypoint'] = new_entrypoint

            container = dc.containers.create(**create_kwargs)

            for path, file in config['files'].items():
                dirname, filename = os.path.split(path)
                utils.DynamicTar.from_str(filename, file).send_to_container(container, dirname)
                print(path, 'loaded', flush=True, end='; ')

            container.start()
            print(container.name, container.short_id, flush=True)

            docker_network_setup_commands = ["DEFAULT=$(/sbin/ip route | awk '/default/ { print $3 }')"]

            eth_i = 0 if first_network is not None else 1

            node_vpn_interfaces = []

            for network, ip in config['networks'].items():
                if network in wireguard_nets:

                    tinc_net_name = prefix + node + '_' + network
                    config_root = os.path.join('/etc/tinc/', tinc_net_name)

                    ssh_exec('mkdir -p ' + os.path.join(config_root, 'hosts'), host_config)

                    write_trough_ssh(config['keys'][0], os.path.join(config_root, 'rsa_key.priv'), host_config)
                    write_trough_ssh(
                        node_tinc_config_template.format(name=node, idx=tun_i),
                        os.path.join(config_root, 'tinc.conf'),
                        host_config)
                    write_trough_ssh(config['tinc'][network], os.path.join(config_root, 'hosts', node), host_config)
                    write_trough_ssh(
                        lab_config['networks'][network]['server_host_config_on_nodes'] if not config['isRouter'] else
                        lab_config['networks'][network]['server_host_config_on_routers'],
                        os.path.join(config_root, 'hosts', 'madt_server'),
                        host_config)
                    write_trough_ssh(
                        node_tinc_up_tempalte.format(
                            c_id=container.short_id,
                            idx=tun_i,
                            ip=config['networks'][network]),
                        os.path.join(config_root, 'tinc-up'),
                        host_config)

                    node_vpn_interfaces.append('tun' + str(tun_i))

                    ssh_exec(
                        '"chmod +x /etc/tinc/{0}/tinc-up; tincd -n {0} -D -d3  > /etc/tinc/{0}/tinc.log 2>&1 &\"'.format(tinc_net_name),
                        host_config)

                    print('[vpn] connected to ' + network, flush=True, end='; ')

                    if 'nat_net' in config and network == config['nat_net']:
                        docker_network_setup_commands.append(
                            "iptables -t nat -A POSTROUTING -o tun{0} -j MASQUERADE".format(tun_i))

                    tun_i += 1

                else:
                    if not network == first_network:
                        host_docker_networks[network].connect(container)
                        print('[dcr] connected to ' + network, flush=True, end='; ')

                    docker_network_setup_commands.append("ip addr add {1} dev eth{0}".format(eth_i, ip))

                    if 'nat_net' in config and network == config['nat_net']:
                        docker_network_setup_commands.append(
                            "iptables -t nat -A POSTROUTING -o eth{0} -j MASQUERADE".format(eth_i))

                    eth_i += 1

            if node_vpn_interfaces:
                tcwrap_config += container.short_id + ' ' + ' '.join(node_vpn_interfaces) + '\n'

            # major routing setup
            if config['routes']:
                for subnet, gateway in config['routes'].items():
                    if subnet == 'default':
                        if config['enableInternet']:
                            subnet = lab_config['subnet']
                        else:
                            docker_network_setup_commands.append("ip route replace default via {0}".format(gateway))
                            continue

                    docker_network_setup_commands.append(
                        "ip route add {0} via {1}".format(subnet, gateway))
            elif not config['enableInternet']:
                docker_network_setup_commands.append("ip route del default")

            if len(docker_network_setup_commands) > 1:
                network_setup_cmd = 'sh -c "' + " && ".join(docker_network_setup_commands) + ';"'
                print(network_setup_cmd)
                (exit_code, out) = container.exec_run(network_setup_cmd)
                if exit_code == 0:
                    print('networking setup ok', flush=True, end='; ')
                else:
                    print('\nERROR WHILE SETTING UP NETWORKING\nReturn code: {0}\nOutput: {1}'.format(exit_code, out),
                          flush=True)

            else:
                print('No network setup')

            if config['tc_options']:
                tc_options_cache[container.short_id] = config['tc_options']
                if config['isRouter']:
                    killed_routers.append(container.name)

            containers.append(container)
            print('\n', flush=True, end='')

        write_trough_ssh(
            tcwrap_config,
            os.path.join('/etc/tcwrap/', lab_name),
            host_config)

        ret[host] = (containers, host_config['docker_networks'])

    print('...done', flush=True)

    waiting_time = 0

    while waiting_time < timeout and not check_routing(lab_config, prefix, choice(list(host_configs.values()))):
        time.sleep(poll_interval)
        waiting_time += poll_interval

    if waiting_time > timeout:
        print('TIMEOUT')

    print('...routing ready, applying tc_options...', flush=True)

    print(ret)

    for host, host_config in host_configs.items():
        for c in ret[host][0]:
            tc_options = tc_options_cache.get(c.short_id, default_tc_options)
            if not tc_options:
                continue
            return_code = tcset_api(c.short_id, tc_options, host_config)
            print('[ TCSET ]', c.short_id, 'SUCCESS' if return_code == 0 else 'FAILED')

    forward_socket(prefix, socket_path, socket_path, host_configs)

    return ret, killed_routers


# pid filenames will include prefix+node_name, it'll make them surely unique
kill_em_all_script = """for file in /var/run/{0}*
do
    pid=$(cat $file);
    kill $pid;
done 
"""


def stop_lab(lab_path, prefix, host_map, host_configs, remove=True):
    lab_config = utils.load_lab_config(lab_path)
    lab_name = os.path.basename(lab_path)

    print('killing tincd on server...', flush=True)
    ret = subprocess.run(kill_em_all_script.format('tinc.' + prefix), shell=True, capture_output=True)
    print('[ out ]', ret.stdout.decode(), ret.stderr.decode(), sep='\n')
    print('\n...done', flush=True)

    print('killing ssh tunnels on server...', flush=True)
    ret = subprocess.run(kill_em_all_script.format('ssh.' + prefix), shell=True, capture_output=True)
    print('[ out ]', ret.stdout.decode(), ret.stderr.decode(), sep='\n')
    print('\n...done', flush=True)

    # TODO: stop socket forwarding
    print('\n\n[ STOP ]', host_map, '\n', host_configs)

    for host in host_map.keys():
        host_config = host_configs[host]
        dc = get_docker_api(host_config)

        print('killing tincd on {}...'.format(host), flush=True)
        ssh_exec(kill_em_all_script.format('tinc.' + prefix), host_config)
        print('\n...done', flush=True)

        print('removing sockets on {}...'.format(host), flush=True)
        ssh_exec('rm -r /sockets/' + lab_name, host_config)
        print('\n...done', flush=True)

        print('killing containers on {}...'.format(host), flush=True)
        for name in host_map[host]['nodes']:
            try:
                if remove: # host and networks in db stored with full names
                    dc.api.remove_container(name, force=True)
                else:
                    dc.api.stop(prefix + name)
                print(name, flush=True, end=' ')
            except docker.errors.NotFound:
                print(name, 'error!', flush=True, end=' ')
        print('\n...done', flush=True)

        if remove:
            print('removing nets on {}...'.format(host), flush=True)
            for name in host_map[host]['networks']:
                try:
                    network = dc.networks.get(prefix+name)
                    network.remove()
                    print(name, flush=True, end=' ')
                except docker.errors.NotFound:
                    print(name, 'not found!', flush=True, end=' ')
            print('\n...done', flush=True)


    print('Ready', flush=True)


def restart_lab(lab_path, prefix, old_host_map, new_host_configs, default_tc_options={}):
    stop_lab(lab_path, prefix, old_host_map, new_host_configs)
    return start_lab(lab_path, prefix, new_host_configs, default_tc_options=default_tc_options)


# ToDo: health check for private networks
def check_routing(lab_config, prefix, host_config):
    dc = get_docker_api(host_config)
    nodes = {name: config for (name, config) in lab_config['nodes'].items() if
             config['image'] != 'quagga' and config['networks']}

    ip_list = [next(iter(config['networks'].values())).split('/')[0] for config in nodes.values()]
    ip_list = [ip for ip in ip_list if not utils.is_private(ip)]
    base_node = choice(list(host_config['nodes']))

    # if not all([utils.is_private(ip) for ip in ip_list]):


    print('from ' + base_node + ':')

    cmd = " && ".join(['ping -c1 -w1 ' + ip for ip in ip_list])
    cmd = "sh -c \"{0}\"".format(cmd)

    container = dc.containers.get(prefix + base_node)
    status, output = container.exec_run(cmd)
    print(output.decode())

    return True if status == 0 else False




def tcset_api(c_id, options, host_config):
    """Temporary placeholder before both matd_ui and madt_lib will move to
        direct use of tcconfig module.
    """
    tcset_options = []
    delay_set = False

    # settings with units
    if 'rate' in options and options['rate'] >= 0:
        if 'rate_unit' in options and options['rate_unit'] in ['Kbps', 'Mbps', 'Gbps']:
            rate_unit = options['rate_unit']
        else:
            rate_unit = 'Mbps'
        tcset_options.append('--rate ' + str(options['rate']) + rate_unit)

    if 'delay' in options and options['delay'] >= 0:
        delay_set = True
        if 'delay_unit' in options and options['delay_unit'] in ['usec', 'msec', 'sec', 'min']:
            delay_unit = options['delay_unit']
        else:
            delay_unit = 'msec'
        tcset_options.append('--delay ' + str(options['delay']) + delay_unit)

    if 'delay-distro' in options:

        if 'delay-distro_unit' in options and options['delay-distro_unit'] in ['usec', 'msec', 'sec', 'min']:
            delay_dist_unit = options['delay-distro_unit']
        else:
            delay_dist_unit = 'msec'

        if not delay_set:
            return "Error: delay distribution can only be set with the delay", 400
        tcset_options.append('--delay-distro ' + str(options['delay-distro']) + delay_dist_unit)

    # settings without units (percentage)
    if 'loss' in options and 0 <= options['loss'] <= 100:  # | ||
        tcset_options.append('--loss ' + str(options['loss']) + '%')  # | |_

    if 'corrupt' in options and 0 <= options['corrupt'] <= 100:
        tcset_options.append('--corrupt ' + str(options['corrupt']) + '%')

    if 'reorder' in options and 0 <= options['reorder'] <= 100:
        if not delay_set:
            return "Error: reordering can only be set with the delay", 400
        tcset_options.append('--reordering ' + str(options['reorder']) + '%')

    if 'duplicate' in options and 0 <= options['duplicate'] <= 100:
        tcset_options.append('--duplicate ' + str(options['duplicate']) + '%')

    if not len(tcset_options):
        return 'Error: no settings were given', 400

    # print('[ TCSET OPTIONS ]', tcset_options, sep='\n', end='\n')

    # print('[ c_id ]', c_id, sep='\n', end='\n')

    cmd = 'tcdel --docker --all {0};\ntcset --docker {1}  {0}'.format(c_id, ' '.join(tcset_options))

    # print('[ CMD ]', cmd, sep='\n', end='\n')


    returncode, stdout = ssh_exec(cmd, host_config)


    print('[ returncode ] ', returncode)
    print('[ stdout ]', stdout, sep='\n')
    # print('[ stderr ]', stderr, sep='\n')

    # return redirect(url_for('show_container', c_id=c_id))

    return returncode
