import subprocess
import json
import peewee
from models import Node
from madt_lib.runtimes.cluster_runtime import ssh_exec, tcset_api


from quart import Blueprint, abort, request, render_template, jsonify, redirect, url_for

net_control_bp = Blueprint('net_control', __name__)

import docker

try:
    from werkzeug.contrib.cache import UWSGICache as cache

    routers_cache = cache()
except:
    from werkzeug.contrib.cache import SimpleCache as cache

    routers_cache = cache()
time_unit_map = [('us', 'usec'), ('ms', 'msec'), ('s', 'sec')]


def get_docker_client(c_id):
    try:
        node = Node.get(Node.short_id == c_id)
        return node.host.get_docker_client()

    except peewee.DoesNotExist:
        return docker.from_env()


def get_container_rules(c_id):
    try:
        node = Node.get(Node.short_id == c_id)

        if node.lab.runtime != "cluster":
            raise peewee.DoesNotExist

        return_code, stdout = ssh_exec('tcshow --docker {}'.format(c_id), node.host.get_config())

        stderr = ''

    except peewee.DoesNotExist:
        tcshow_process = subprocess.run(['tcshow', '--docker', c_id], stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, universal_newlines=True)

        return_code = tcshow_process.returncode
        stdout = tcshow_process.stdout
        stderr = tcshow_process.stderr

    print('[ returncode ]', return_code, sep='\n', end='\n')
    print('[ stdout ]', stdout, sep='\n', end='\n')
    print('[ stderr ]', stderr, sep='\n', end='\n')

    data = json.loads(stdout[:stdout.rfind('}')+1])

    try:
        data = data.popitem()[1]['outgoing']['protocol=ip']
    except (KeyError, IndexError):
        data = {}
    print(data)

    ret = {}

    for k in ['loss', 'duplicate', 'corrupt', 'reorder']:
        if k in data and data[k] != "None":
            ret[k] = int(data[k][:-1])
        else:
            ret[k] = 0

    for k in ['delay', 'delay-distro']:
        if k in data and data[k] != "None":
            ret[k] = int(data[k].split('.')[0])
            # s will be last, so its ok
            ret[k + '_unit'] = next(filter(lambda i: i[0] in data[k], time_unit_map), [None, 'sec'])[1]
        else:
            ret[k] = 0
            ret[k + '_unit'] = 'msec'

    if "rate" in data and data['rate'] != "None":
        ret['rate'] = int(data["rate"][:-4])
        ret['rate_unit'] = data["rate"][-4:]

    return ret


def check_delay(data):
    # TODO
    return True


def to_int(data, int_keys):
    ret = {}

    for k in data.keys():
        if k in int_keys: 
            if data[k] != '':
                ret[k] = int(data[k])
        else:
            ret[k] = data[k]

    return ret


# TODO: more general way to decide if container is a router
def is_router(container):
    return 'quagga' in container.image.tags[0]


@net_control_bp.route('/container/<string:c_id>')
async def show_container(c_id):
    lab = request.args.get('lab', 'DEMO')

    try:
        n = Node.get(Node.name == c_id)
        print('yeah, its a node name')
        return redirect(url_for('net_control.show_container', c_id=n.short_id, lab=lab))
    except peewee.DoesNotExist:
        print('yeah, its not a node name for sure')
        pass

    print('getting client')

    dc = get_docker_client(c_id)

    try:
        container = dc.containers.get(c_id)
    except docker.errors.NotFound:
        return abort(404)

    # processes = '; '.join([p[-1] for p in container.top(ps_args='-ww')['Processes']])
    processes = "FIXME"
    if processes:
        processes += ';'

    networks = '; '.join(container.attrs['NetworkSettings']['Networks'].keys())
    if networks:
        networks += ';'

    rules = get_container_rules(c_id)

    return await render_template('container_view.html', container=container,
                           processes=processes, networks=networks,
                           rules=rules, lab=lab)


@net_control_bp.route('/tcget', methods=['GET', ])
async def tcget():

    c_id = request.args.get('id')
    if c_id is None:
        return abort(404)

    dc = get_docker_client(c_id)

    try:
        dc.containers.get(c_id)
    except docker.errors.NotFound:
        return abort(404)

    return jsonify(get_container_rules(c_id))



@net_control_bp.route('/tcset', methods=['POST', ])
async def tcset():
    data = await request.json

    c_id = request.args.get('id')
    if c_id is None:
        if data is None or 'id' not in data:
            return abort(400)
        c_id = data.get('id')
    else:
        data = await request.form

    try:
        data = to_int(data, ['rate', 'delay', 'loss',
                                     'corrupt', 'reorder', 'duplicate', 'delay-distro'])
    except ValueError:
        return "Error: wrong value, only integers are allowed", 400
    except TypeError:
        return "Error: invalid request body", 400

    # print(data)

    tcset_options = []
    delay_set = False

    # settings with units
    if 'rate' in data and data['rate'] > 0:
        if 'rate_unit' in data and data['rate_unit'] in ['Kbps', 'Mbps', 'Gbps']:
            rate_unit = data['rate_unit']
        else:
            rate_unit = 'Mbps'

        tcset_options.append('--rate ' + str(data['rate']) + rate_unit)

    if 'delay' in data and check_delay(data) and data['delay'] > 0:
        delay_set = True
        if 'delay_unit' in data and data['delay_unit'] in ['usec', 'msec', 'sec', 'min']:
            delay_unit = data['delay_unit']
        else:
            delay_unit = 'msec'
        tcset_options.append('--delay ' + str(data['delay']) + delay_unit)

    if 'delay-distro' in data and data['delay-distro'] > 0:
        
        if 'delay-distro_unit' in data and data['delay-distro_unit'] in ['usec', 'msec', 'sec', 'min']:
            delay_dist_unit = data['delay-distro_unit']
        else:
            delay_dist_unit = 'msec'

        if not delay_set:
            return "Error: delay distribution can only be set with the delay", 400
        tcset_options.append('--delay-distro ' + str(data['delay-distro']) + delay_dist_unit)

    # settings without units (percentage)
    if 'loss' in data and 0 <= data['loss'] <= 100:  # | ||
        tcset_options.append('--loss ' + str(data['loss']) + '%')  # | |_

    if 'corrupt' in data and 0 <= data['corrupt'] <= 100:
        tcset_options.append('--corrupt ' + str(data['corrupt']) + '%')

    if 'reorder' in data and 0 <= data['reorder'] <= 100:
        if not delay_set and data['reorder'] > 0:
            return "Error: reordering can only be set with the delay", 400
        tcset_options.append('--reordering ' + str(data['reorder']) + '%')

    if 'duplicate' in data and 0 <= data['duplicate'] <= 100:
        tcset_options.append('--duplicate ' + str(data['duplicate']) + '%')

    if not len(tcset_options):
        return 'Error: no settings were given', 400

    print('[ TCSET OPTIONS ]', tcset_options, sep='\n', end='\n')

    print('[ c_id ]', c_id, sep='\n', end='\n')

    if all([data[k] == 0 for k in ['loss', 'corrupt', 'reorder', 'duplicate', 'delay']]):
        cmd = 'tcdel --all --docker ' + c_id
    else:
        cmd = 'tcset --overwrite --docker {}  {}'.format(c_id, ' '.join(tcset_options))

    print('[ CMD ]', cmd, sep='\n', end='\n')

    try:
        node = Node.get(Node.short_id == c_id)

        if node.lab.runtime != 'cluster':
            raise peewee.DoesNotExist

        host = node.host
        dc = host.get_docker_client()
        lab_name = node.lab.name

        return_code, stdout = ssh_exec('tcwrap ' + cmd + ' --lab ' + lab_name, host.get_config())

        stderr = ''

    except peewee.DoesNotExist:
        dc = docker.from_env()

        tcset_process = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, universal_newlines=True,
                                       timeout=25)

        return_code = tcset_process.returncode
        stdout = tcset_process.stdout
        stderr = tcset_process.stderr

    print('[ returncode ] ', return_code)
    print('[ stdout ]', stdout, sep='\n')
    print('[ stderr ]', stderr, sep='\n')

    # return redirect(url_for('show_container', c_id=c_id))

    container = dc.containers.get(c_id)

    if cmd[:5] == 'tcdel':
        return 'OK', 200

    if return_code == 0:
        if is_router(container):
            routers_cache.set(container.name, True)

        return 'OK', 200
    else:
        return jsonify({
            'returncode': return_code,
            'stdout': stdout,
            'stderr': stderr
        }), 400


@net_control_bp.route('/tcdel', methods=['POST', ])
async def tcdel():

    data = await request.json
    if data is None or 'id' not in data:
        return abort(400)

    c_id = data.get('id')

    dc = get_docker_client(c_id)
    try:
        container = dc.containers.get(c_id)
    except docker.errors.NotFound:
        return abort(404)

    cmd = 'tcdel --all --docker ' + c_id

    print('[ CMD ]', cmd, sep='\n', end='\n')

    try:
        node = Node.get(Node.short_id == c_id)

        if node.lab.runtime != 'cluster':
            raise peewee.DoesNotExist

        host = node.host
        dc = host.get_docker_client()
        lab_name = node.lab.name

        return_code, stdout = ssh_exec('tcwrap ' + cmd + ' --lab ' + lab_name, host.get_config())

        stderr = ''

    except peewee.DoesNotExist:
        dc = docker.from_env()

        tcset_process = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, universal_newlines=True,
                                       timeout=25)

        return_code = tcset_process.returncode
        stdout = tcset_process.stdout
        stderr = tcset_process.stderr


    print('[ returncode ] ', return_code)
    print('[ stdout ]', stdout, sep='\n')
    print('[ stderr ]', stderr, sep='\n')

    container = dc.containers.get(c_id)

    if is_router(container):
        routers_cache.delete(container.name)

    return 'OK', 200
