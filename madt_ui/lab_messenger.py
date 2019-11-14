from threading import Thread, Event
import os
import time
import asyncio
import zmq
import zmq.asyncio
from zmq.utils import jsonapi

from config import lab_path, prefix

try:
    from werkzeug.contrib.cache import UWSGICache as cache
    msg_cache = cache()
except:
    from werkzeug.contrib.cache import SimpleCache as cache
    msg_cache = cache()

ctx = zmq.asyncio.Context()

class Messenger:
    def __init__(self, lab_name):
        self.lab_name = lab_name
        self.prefix = prefix(lab_name)
        msg_cache.set(lab_name, {
            'all': {},
            'status_count': {},
            'total': 0,
            'avg_traffic': 0,
            'start_time': int(time.time())
        })
        self.sock = ctx.socket(zmq.PULL)

        url = self.socket_url()
        self.sock.bind(url)

        asyncio.ensure_future(self.listen())

    def socket_url(self):
        return 'ipc://'+os.path.join(os.environ['MADT_LABS_SOCKETS_DIR'], self.lab_name, 'lab.sock')

    async def listen(self):
        while True:
            await asyncio.sleep(0.25)
            i = 0
            while i < 500:
                i = i+1
                raw_msg = await self.sock.recv()
                msg = jsonapi.loads(raw_msg)

                if 'hostname' in msg:
                    msgs = msg_cache.get(self.lab_name)

                    if msgs is None:
                        return
                    msgs['all'][self.prefix + msg.pop('hostname')] = msg

                    msgs['total'] += 1

                    if msg['status']:
                        if msg['status'] in msgs['status_count']:
                            msgs['status_count'][msg['status']] += 1
                        else:
                            msgs['status_count'][msg['status']] = 1

                    if msg['traffic']:
                        msgs['avg_traffic'] = (msgs['avg_traffic'] + msg['traffic']) / msgs['total']

                    msg_cache.set(self.lab_name, msgs)
                else:
                    print('received message from unknown host: ' + str(msg))

    @staticmethod
    def get_messages(lab_name):
        msgs = msg_cache.get(lab_name)
        if msgs is not None:
            all_messages = msgs['all']
            msgs['all'] = {}
            msg_cache.set(lab_name, msgs)

            return all_messages
        else:
            return None

    @staticmethod
    def get_stats(lab_name):
        msgs = msg_cache.get(lab_name)
        return {k: v for k, v in msgs.items() if k != 'all'} if msgs else msgs

    @staticmethod
    def get_data(lab_name):
        msgs = msg_cache.get(lab_name)
        if msgs is not None:
            msgs_copy = msgs.copy()
            msgs_copy['all'] = {}
            msg_cache.set(lab_name, msgs_copy)

            return msgs
        else:
            return None



