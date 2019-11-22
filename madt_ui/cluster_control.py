from quart import Blueprint, request, jsonify, abort
import peewee
from docker.errors import APIError

from .models import Lab, Node, Host

cluster_control_bp = Blueprint('cluster_control', __name__)


@cluster_control_bp.route('/connect', methods=['POST',])
async def connect_host():

    data = await request.json or request.args or await request.form
    if not data:
        return abort(400)

    name = data.get('name')
    docker_port = data.get('docker_port')
    ssh_port = data.get('ssh_port')

    try:
        Host.get(name=name)
        return 'name already taken', 400
    except peewee.DoesNotExist:
        pass

    address = request.remote_addr

    Host.create(name=name, protocol='tcp', address=address,
                docker_port=docker_port, ssh_port=ssh_port)

    with open('/etc/madt/hosts', 'a') as hosts_file:
        hosts_file.write(str(ssh_port) + '\n')

    with open('/root/.ssh/id_rsa.pub') as public_key_file:
        public_key = public_key_file.read()

    return public_key, 200


@cluster_control_bp.route('/status')
async def refresh_status():
    hosts = Host.select()

    if not hosts:
        return jsonify([])

    for host in hosts:
        try:
            host.get_docker_client().ping()
            host.is_alive = True
        except:
            host.is_alive = False

    Host.bulk_update(hosts, fields=[Host.is_alive])

    return jsonify({h.name: h.is_alive for h in hosts})


@cluster_control_bp.route('/remove_host')
async def remove_host():
    try:
        id = await request.json.get('id', int)
    except ValueError:
        abort(404)

    Host.delete_by_id(id)

    return 'OK', 200
