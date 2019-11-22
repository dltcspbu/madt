import pytest
import docker
import requests
from quart import Quart
import asyncio
import json

import madt_ui
import madt_ui.config
from madt_ui import models
from madt_ui import net_control
import madt_ui.main as main
from madt_ui.login import login

app = main.app
dc = docker.from_env()

@pytest.fixture(name='madt_ui')
def _test_app():
    return app


class TestClass:
    def setup_method(self):
        self.corrupt = 10
        self.delay = 20
        self.delay_distro = 1
        self.delay_distro_unit = 'msec'
        self.delay_unit = 'msec'
        self.duplicate = 40
        self.loss = 50
        self.rate = 1
        self.rate_unit = 'Gbps'
        self.reorder = 70
        self.json_ans  = {'rate':self.rate, 'rate_unit': self.rate_unit,
                                   'delay-distro':self.delay_distro,
                                   'delay-distro_unit':self.delay_distro_unit,
                                   'loss': self.loss, 'corrupt': self.corrupt, 
                                   'reorder': self.reorder, 'duplicate': self.duplicate, 
                                   'delay': self.delay, 'delay_unit': self.delay_unit}
    @pytest.mark.asyncio
    async def test_tcset(self):

        test_client = app.test_client()
        c = dc.containers.run("alpine", detach=True, entrypoint="tail -f /dev/null")
        response = await test_client.post('/login',form={'username': 'demo', 'password': 'demo'})
        assert response.status_code == 302

        response = await test_client.post('/tcset',
                                          query_string={'id': c.short_id},
                                          form = self.json_ans)
        assert response.status_code == 200
        
        response = await test_client.get('/tcget', query_string={'id': c.short_id})
        assert response.status_code == 200

        rj_answer = (await response.get_json())
        assert  (rj_answer['rate'] == self.json_ans['rate'] and 
                 rj_answer['corrupt'] == self.json_ans['corrupt'] and
                 rj_answer['delay'] == self.json_ans['delay'] and
                 rj_answer['rate_unit'] == self.json_ans['rate_unit'] and
                 rj_answer['loss'] == self.json_ans['loss'] and
                 rj_answer['duplicate'] == self.json_ans['duplicate'] and
                 rj_answer['delay_unit'] == self.json_ans['delay_unit'] and
                 rj_answer['delay-distro'] == self.json_ans['delay-distro'] and
                 rj_answer['delay-distro_unit'] == self.json_ans['delay-distro_unit'] and
                 rj_answer['reorder'] == self.json_ans['reorder'] 
                )

        c.remove(force=True)


"""
@pytest.mark.asyncio
async def test_tcget(madt_ui):
    datastring = "rate=&rate_unit=Kbps&delay=0&delay_unit=msec&delay-distro=0&delay-distro_unit=msec&loss=27&corrupt=0&duplicate=0&reorder=0"
    c_id = '26069c607154'
    test_client = app.test_client()
    response = await test_client.get('/tcget?id=26069c607154')
    res = await response.get_json()
    assert res == datastring 
"""
