from quart import Blueprint, render_template, request, jsonify
import os
import json

from .lab2graph import from_config
from .config import lab_path, prefix

from .lab_messenger import Messenger
from .net_control import routers_cache

lab_visual_bp = Blueprint('lab_visual', __name__)


@lab_visual_bp.route('/graph')
async def show_graph():
    lab = request.args.get('lab', 'DEMO')
    return await render_template('graph.html', lab=lab, prefix=prefix(lab))


@lab_visual_bp.route('/graph.json')
async def generate_graph_json():
    lab = request.args.get('lab', 'DEMO')
    return jsonify(from_config(os.path.join(lab_path(lab), 'lab.json')))


@lab_visual_bp.route('/messages.json')
async def get_messages():

    lab = request.args.get('lab', 'DEMO')

    messages = Messenger.get_messages(lab)

    lab_prefix = prefix(lab)

    with open(os.path.join(lab_path(lab), 'lab.json')) as config_file:
        lab_config = json.load(config_file)

    for name, config in lab_config['nodes'].items():
        fullname = lab_prefix + name

        # print(routers_cache, fullname, config)
        if not config['isRouter']:
            continue

        if routers_cache.has(fullname):
            messages[fullname] = {
                'status': 1
            }
        
    print('[ msg ]', messages)
    return jsonify(messages)

