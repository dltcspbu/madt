import pytest
import docker
import requests
from quart import Quart
import asyncio
import json
import os

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
        self.passwd = 'demo'
        os.environ["SSH_PWD"] = self.passwd
        self.already_set = []
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
        self.test_client = app.test_client()
        self.container = dc.containers.run("alpine", detach=True, entrypoint="tail -f /dev/null")
        self.json_ans  = {'rate':self.rate, 'rate_unit': self.rate_unit,
                                   'delay-distro':self.delay_distro,
                                   'delay-distro_unit':self.delay_distro_unit,
                                   'loss': self.loss, 'corrupt': self.corrupt, 
                                   'reorder': self.reorder, 'duplicate': self.duplicate, 
                                   'delay': self.delay, 'delay_unit': self.delay_unit}

    def teardown_module(self):
        self.container.remove(force=True)

    async def login(self):
        response = await self.test_client.post('/login',form={'username': 'demo', 'password': self.passwd})
        assert response.status_code == 302

    async def tcset_param(self, param_name):
        status = await self.login()
        response = await self.test_client.post('/tcset',
                                          query_string={'id': self.container.short_id},
                                          form = {param_name: self.json_ans[param_name]})
        assert response.status_code == 200
        
        response = await self.test_client.get('/tcget', query_string={'id': self.container.short_id})
        assert response.status_code == 200

        rj_answer = (await response.get_json())
        self.already_set.append(param_name)

        print('\n\n sent: ', self.json_ans)
        print('\n\n received: ', rj_answer)
        print('\n\n already_set: ', self.already_set)

        assert all([rj_answer[k] == self.json_ans[k] for k in self.already_set])

    @pytest.mark.asyncio
    async def test_login(self):
        status = await self.login()

    @pytest.mark.asyncio
    async def test_tcset(self):

        stcode = await self.login()
        response = await self.test_client.post('/tcset',
                                          query_string={'id': self.container.short_id},
                                          form = self.json_ans)
        assert response.status_code == 200
        
        response = await self.test_client.get('/tcget', query_string={'id': self.container.short_id})
        assert response.status_code == 200

        rj_answer = (await response.get_json())
        assert all([rj_answer[k] == self.json_ans[k]] 
                for k in ['rate', 'corrupt', 'delay', 'rate_unit', 'loss', 
                          'duplicate', 'delay_unit', 'delay-distro', 'delay-distro_unit', 'reorder'])

    @pytest.mark.asyncio
    async def test_tcsee_corrupt(self):
        status = await self.tcset_param(param_name='corrupt')

    @pytest.mark.asyncio
    async def test_tcsee_delay_n_dublicate(self):
        status = await self.tcset_param(param_name='delay')
        status = await self.tcset_param(param_name='duplicate')

    @pytest.mark.asyncio
    async def test_tcsee_loss(self):
        status = await self.tcset_param(param_name='loss')

    @pytest.mark.asyncio
    async def test_tcsee_delay(self):
        status = await self.tcset_param(param_name='delay')

    @pytest.mark.asyncio
    async def test_tcsee_dublicate(self):
        status = await self.tcset_param(param_name='duplicate')

    @pytest.mark.asyncio
    async def test_tcsee_rate(self):
        status = await self.tcset_param(param_name='rate')

