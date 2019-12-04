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

    async def tcset_param(self, param_names):
        status = await self.login()

        for name in param_names:
            response = await self.test_client.post('/tcset',
                                          query_string={'id': self.container.short_id},
                                          form = {name: self.json_ans[name]})
            assert response.status_code == 200
        
        response = await self.test_client.get('/tcget', query_string={'id': self.container.short_id})
        assert response.status_code == 200

        rj_answer = (await response.get_json())

        print('\n\n received: ', rj_answer)
        print('\n\n tobe_set: ', param_names)

        assert all([rj_answer[k] == self.json_ans[k] for k in param_names])

    @pytest.mark.asyncio
    async def test_login(self):
        status = await self.login()

    # Test multople parameter set by the same request
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
        status = await self.tcset_param(param_names=['corrupt'])

    @pytest.mark.asyncio
    async def test_tcsee_delay_n_dublicate(self):
        status = await self.tcset_param(param_name=['delay', 'duplicate'])

    @pytest.mark.asyncio
    async def test_tcsee_loss(self):
        status = await self.tcset_param(param_names=['loss'])

    @pytest.mark.asyncio
    async def test_tcsee_delay(self):
        status = await self.tcset_param(param_names=['delay'])

    @pytest.mark.asyncio
    async def test_tcsee_dublicate(self):
        status = await self.tcset_param(param_names=['duplicate'])

    @pytest.mark.asyncio
    async def test_tcsee_rate(self):
        status = await self.tcset_param(param_names=['rate'])

