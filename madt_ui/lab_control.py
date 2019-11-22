from quart import Blueprint, render_template, request, jsonify, abort
import time
import peewee
import os

from madt_lib.runtime_api import restart_lab, stop_lab, start_lab

from .lab_messenger import Messenger, msg_cache
from .config import prefix, lab_path
from .models import Host, Lab, Node, Network
from .net_control import routers_cache

lab_control_bp = Blueprint('lab_control', __name__)


try:
    runtime = os.environ['MADT_RUNTIME']
except KeyError:
    runtime = 'docker'

@lab_control_bp.route('/lab/<string:name>')
async def list_containers(name):
    # hosts = Host.select()
    if not os.path.exists(lab_path(name)):
        abort(404)

    containers = []

    show_containers = 'show_containers' in request.args and request.args['show_containers'] == 'True'

    if show_containers:
        try:
            lab = Lab.get(Lab.name == name)
            containers = lab.list_containers()
        except peewee.DoesNotExist:
            pass

    stats = Messenger.get_stats(name)
    if stats and 'start_time' in stats:
        stats['uptime'] = int(time.time() - stats['start_time'])

    return await render_template('containers_list.html', containers=containers, lab=name, stats=stats, show_containers=show_containers)


@lab_control_bp.route('/lab/containers')
async def get_lab_containers():
    name = request.args.get('name')
    if name is None:
        return abort(400)
        
    if not os.path.exists(lab_path(name)):
        abort(404)

    try:
        lab = Lab.get(Lab.name == name)
        containers = lab.list_containers()
    except peewee.DoesNotExist:
        containers = []

    prefix_len = len(prefix(name))

    return jsonify({c.name[prefix_len:]: c.short_id for c in containers})



@lab_control_bp.route('/lab/restart', methods=['POST', ])
async def restart_lab_api():
    '''
    try:
        hosts_ids = request.json.get('hosts', list)
    except (ValueError, AttributeError):
        return abort(400)

    hosts = Host.select().where(Host.id in hosts_ids)

    if len(hosts) == 0:
        return abort(400)
    elif len(hosts) == 1:
        runtime = 'docker'
    else:
        runtime = 'cluster'
    '''

    data = await request.json

    if data is None or 'name' not in data:
        return abort(400)
        
    name = data.get('name')

    lab, created = Lab.get_or_create(name=name, defaults={'runtime': runtime})

    tc_options = data.get('tc_options', {})
    hosts = Host.get_all_configs()

    if created:
        ret, killed_routers = start_lab(lab_path(name),
                                          prefix(name),
                                          *(() if runtime!='cluster' else \
                                                (hosts,)),
                                          default_tc_options=tc_options,
                                          runtime=runtime)
    else:
        ret, killed_routers = restart_lab(lab_path(name),
                                        prefix(name),
                                        *(() if runtime!='cluster' else \
                                            (lab.get_host_map(), hosts)),
                                        default_tc_options=tc_options,
                                        runtime=runtime)
        print('\n[ deleting old nodes & network ]\n')
        Node.delete().where(Node.lab_id == lab.id).execute()
        Network.delete().where(Network.lab_id == lab.id).execute()

    print('\n[ mid-state ]', list(Node.select()))

    if runtime == 'cluster':
        hosts_map = ret
        for host_name, (containers, networks) in ret.items():
            Node.bulk_create([Node(name=c.name, short_id=c.short_id, lab=lab, host_id=hosts[host_name]['id']) for c in containers])
            Network.bulk_create([Network(name=n, lab=lab, host=hosts[host_name]['id']) for n in networks])

    msgr = Messenger(name)

    # with open(os.path.join('/sockets', name, 'lab.sock'), 'w') as f:
    #     f.write('no')
    

    for container_name in killed_routers:
        routers_cache.set(container_name, True)

    return 'OK', 200



@lab_control_bp.route('/lab/stop', methods=['POST', ])
async def stop_lab_api():

    data = await request.json

    if data is None or 'name' not in data:
        return abort(400)

    name = data.get('name')

    try:
        lab = Lab.get(Lab.name == name)
    except peewee.DoesNotExist:
        abort(404)

    try:
        args = []
        if lab.runtime == 'cluster':
            args.extend((lab.get_host_map(), Host.get_all_configs()))

        stop_lab(lab_path(name), prefix(name), *args, runtime=lab.runtime, remove=True)
        lab.delete_instance()
        msg_cache.delete(name)
        return 'OK', 200

    except FileNotFoundError:
        return abort(404)


@lab_control_bp.route('/lab/stats')
async def get_stats():
    name = request.args.get('name')
    if name is None:
        return abort(400)

    ret = Messenger.get_stats(name)
    if ret is not None:
        return jsonify(ret)
    else:
        return abort(404)

