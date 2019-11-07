import docker
import os
from random import choice
import time
import shutil
import subprocess


from .. import utils


def format_entrypoint(ep):
    if type(ep) is str:
        return ep
    return ' ' + ' '.join(['"{}"'.format(cmd) for cmd in ep])


def start_lab(lab_path, prefix, image_prefix='', timeout=3*60, poll_interval=10, default_tc_options={}):
    lab_config = utils.load_lab_config(lab_path)

    dc = docker.from_env()

    lab_name = os.path.basename(lab_path)

    # socket management
    try:
        # in-container case
        socket_dir = os.environ['LABS_SOCKETS_DIR']
    except KeyError:
        socket_dir = os.path.abspath('./sockets/')
    socket_dir = os.path.join(socket_dir, lab_name)

    try:
        os.remove(os.path.join(socket_dir, 'lab.sock'))
    except FileNotFoundError:
        pass

    docker_networks = {}
    print('creating networks...', flush=True)
    for network, config in lab_config['networks'].items():
        print(network, flush=True)

        masklen = config['subnet'].split('/')[1]

        '''docker_networks[network] = dc.networks.create(prefix+network, ipam=docker.types.IPAMConfig(driver='mini',
            options={'com.github.mini.cidr_mask_length': masklen}))'''

        docker_networks[network] = dc.networks.create(prefix + network, driver='bridge')
    print('...done', flush=True)

    image_cache = {}
    tc_options_cache = {}
    killed_routers = []

    ret = []
    print('setting up containers...', flush=True)
    for node, config in lab_config['nodes'].items():
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
            'volumes': {socket_dir: {'bind': '/lab', 'mode':'rw'}},
            'detach': True,
            'cap_add': ["NET_ADMIN"],
            'version': dc.api._version,
        }

        if not config['enableInternet']:
            first_network = next(iter(config['networks']), None)
            if first_network is not None:
                create_kwargs['network'] = docker_networks[first_network].name
        else:
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
                            original_entrypoint[i+1] == '-c':
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

        c = dc.containers.create(**create_kwargs)

        for path, file in config['files'].items():
            dirname, filename = os.path.split(path)
            utils.DynamicTar.from_str(filename, file).send_to_container(c, dirname)
            print(path, 'loaded', flush=True, end='; ')

        for path, b64 in config['directories'].items():
            base_dir = os.path.split(path)[0]
            utils.DynamicTar.from_base64(b64).send_to_container(c, base_dir)
            print(path, 'loaded', flush=True, end='; ')

        c.start()
        print(c.name, c.short_id, flush=True)

        network_setup_commands = []
        # todo: fix default route on gateway
        i = 1 if config['enableInternet'] else 0
        for network, ip in config['networks'].items():
            if not network == first_network:
                docker_networks[network].connect(c)
                print('connected to '+network, flush=True, end='; ')

            # network_setup_cmd += "ip addr flush eth{0}; ip addr add {1} dev eth{0}; ".format(i, ip)
            network_setup_commands.append("ip addr add {1} dev eth{0}".format(i, ip))

            if 'nat_net' in config and network == config['nat_net']:
                network_setup_commands.append("iptables -t nat -A POSTROUTING -o eth{0} -j MASQUERADE".format(i))

            i += 1

        if config['routes']:
            for subnet, gateway in config['routes'].items():
                if subnet == 'default':
                    if config['enableInternet']:
                        subnet = lab_config['subnet']
                    else:
                        network_setup_commands.append("ip route replace default via {0}".format(gateway))
                        continue

                network_setup_commands.append(
                    "ip route add {0} via {1}".format(subnet, gateway))
        elif not config['enableInternet']:
            network_setup_commands.append("ip route del default")

        if network_setup_commands:
            network_setup_cmd = 'sh -c "' + " && ".join(network_setup_commands) + ';"'
            print(network_setup_cmd)
            (exit_code, out) = c.exec_run(network_setup_cmd)
            if exit_code == 0:
                print('networking setup ok', flush=True, end='; ')
            else:
                print('\nERROR WHILE SETTING UP NETWORKING\nReturn code: {0}\nOutput: {1}'.format(exit_code, out),
                      flush=True)

        else:
            print('No network setup')

        if config['tc_options']:
            tc_options_cache[c.short_id] = config['tc_options']
            if config['isRouter']:
                killed_routers.append(c.name)

        ret.append(c.short_id)
        print('\n', flush=True, end='')

    print('...done, waiting for routing...', flush=True)

    waiting_time = 0

    while waiting_time < timeout and not check_routing(lab_config, prefix, dc=dc):
        time.sleep(poll_interval)
        waiting_time += poll_interval

    if waiting_time > timeout:
        print('TIMEOUT')

    print('...routing ready, applying tc_options...', flush=True)
    for c_id in ret:
        tc_options = tc_options_cache.get(c_id, default_tc_options)
        if not tc_options:
            continue
        return_code = tcset_api(c_id, tc_options)
        print('[ TCSET ]', c_id, 'SUCCESS' if return_code == 0 else 'FAILED')

    return ret, killed_routers


def restart_lab(lab_path, prefix, **kwargs):
    """Stops the running simulation and starts it again.
        Arguments are same as those of start_lab"""

    stop_lab(lab_path, prefix)
    ret = start_lab(lab_path, prefix, **kwargs)

    print('\n...done', flush=True)

    return ret



def stop_lab(lab_path, prefix, remove=True):
    lab_config = utils.load_lab_config(lab_path)
    dc = docker.from_env()

    print('killing containers...', flush=True)
    for name in lab_config['nodes'].keys():
        try:
            if remove:
                dc.api.remove_container(prefix+name, force=True)
            else:
                dc.api.stop(prefix + name)
            print(name, flush=True, end=' ')
        except docker.errors.NotFound:
            print(name, 'error!', flush=True, end=' ')
    print('\n...done', flush=True)

    if remove:
        print('removing nets...', flush=True)
        for name in lab_config['networks'].keys():
            try:
                for n in dc.networks.list(prefix + name):
                    # network = dc.networks.get(prefix + name)
                    n.remove()
                print(name, flush=True, end=' ')
            except docker.errors.NotFound:
                print(name, 'not found!', flush=True, end=' ')
        print('\n...done', flush=True)

    print('Ready', flush=True)


max_nodes = 32
def check_routing(lab_config, prefix, dc=docker.from_env()):
    nodes = {name: config for (name, config) in lab_config['nodes'].items() if config['image'] != 'madt/quagga' and config['networks']}

    if not nodes:
        return True

    ip_list = [next(iter(config['networks'].values())).split('/')[0] for config in nodes.values()]
    base_node = choice(list(nodes.keys()))

    # do not test private IPs from public ones
    if not all([utils.is_private(ip) for ip in ip_list]):
        ip_list = [ip for ip in ip_list if not utils.is_private(ip)]

    print('from ' + base_node + ':')

    
    if max_nodes < len(ip_list):
        cmd = " && ".join(['ping -c1 -w1 ' + choice(ip_list) for i in range(max_nodes)])
    else:
        cmd = " && ".join(['ping -c1 -w1 ' + ip for ip in ip_list])
    cmd = "sh -c \"{0}\"".format(cmd)

    container = dc.containers.get(prefix+base_node)
    status, output = container.exec_run(cmd)
    print(output.decode(), flush=True)

    return True if status == 0 else False




def tcset_api(c_id, options):
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


    tcset_process = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, universal_newlines=True,
                                       timeout=25)

    return_code = tcset_process.returncode
    stdout = tcset_process.stdout
    stderr = tcset_process.stderr

    # print('[ returncode ] ', return_code)
    # print('[ stdout ]', stdout, sep='\n')
    # print('[ stderr ]', stderr, sep='\n')

    # return redirect(url_for('show_container', c_id=c_id))

    return return_code
