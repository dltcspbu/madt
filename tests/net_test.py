import madt_ui.main as main

import pytest
import docker
import requests
from quart import Quart
import asyncio
import json
import os

from madt_ui import models
from madt_ui import net_control
from madt_ui.login import login

app = main.app
dc = docker.from_env()

@pytest.fixture(name='madt_ui')
def _test_app():
    return app


class TestClass:

    def setup_method(self):
        self.already_set = []
        self.passwd = 'demo'
        os.environ["SSH_PWD"] = self.passwd
        self.corrupt = 10
        self.corrupt_default = 0
        self.delay = 20
        self.delay_default = 0
        self.delay_distro = 1
        self.delay_distro_deault = 0
        self.delay_distro_unit = 'msec'
        self.delay_distro_unit_default = 'msec'
        self.delay_unit = 'msec'
        self.delay_unit_default = 'msec'
        self.duplicate = 40
        self.duplicate_default = 0
        self.loss = 50
        self.loss_default = 0
        self.rate = 1
        self.rate_default = 10
        self.rate_unit = 'Mbps'
        self.rate_unit_default = 'Gbps'
        self.reorder = 70
        self.reorder_default = 0
        self.update = 'true'
        self.update_default = 'false'
        self.test_client = app.test_client()
        self.container = dc.containers.run("alpine", detach=True, entrypoint="tail -f /dev/null")
        self.json_ans  = {'rate':self.rate, 'rate_unit': self.rate_unit,
                                   'delay-distro':self.delay_distro,
                                   'delay-distro_unit':self.delay_distro_unit,
                                   'loss': self.loss, 'corrupt': self.corrupt, 
                                   'reorder': self.reorder, 'duplicate': self.duplicate, 
                                   'delay': self.delay, 'delay_unit': self.delay_unit,
                                   'update': self.update}
        self.json_default  = {'rate':self.rate_default, 'rate_unit': self.rate_unit_default,
                                   'delay-distro':self.delay_distro_deault,
                                   'delay-distro_unit':self.delay_distro_unit_default,
                                   'loss': self.loss_default, 'corrupt': self.corrupt_default, 
                                   'reorder': self.reorder_default, 'duplicate': self.duplicate_default, 
                                   'delay': self.delay_default, 'delay_unit': self.delay_unit_default,
                                   'update': self.update_default }
        self.fields = ['rate', 'corrupt', 'delay', 'rate_unit', 'loss', 'duplicate', 'delay_unit', 'delay-distro', 'delay-distro_unit', 'reorder'] 

    def teardown_module(self):
        self.container.remove(force=True)

    def str2bool(v):
        return v.lower() in ("yes", "true", "t", "1")

    async def login(self):
        response = await self.test_client.post('/login',form={'username': 'demo', 'password': self.passwd})
        assert response.status_code == 302

    async def tcset_param(self, param_names):
        status = await self.login()
        self.already_set.extend(param_names)
        is_upd = True if 'update' in param_names else False

        response = await self.test_client.post('/tcset',
                                          query_string={'id': self.container.short_id},
                                          form = {name: self.json_ans[name] for name in param_names})
        assert response.status_code == 200
        
        response = await self.test_client.get('/tcget', query_string={'id': self.container.short_id})
        assert response.status_code == 200

        rj_answer = (await response.get_json())

        print('\n\n received: ', rj_answer)
        print('\n\n tobe_set: ', param_names)
        print('\n\n alread_set: ', self.already_set)
        
        print(is_upd)
        if is_upd:
            assert all([rj_answer[k] == self.json_ans[k]  for k in self.already_set if k != 'update'])
            #assert all([rj_answer[k] == self.json_default[k]  for k in self.already_set if k != 'update'])
        else:
            assert all([rj_answer[k] == (self.json_ans[k] if k in param_names else self.json_default[k])  for k in self.already_set if k != 'update' ])
        assert all([rj_answer[k] == self.json_default[k]  for k in self.fields if k != 'update' and k not in self.already_set])

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
        status = await self.tcset_param(param_names=['delay'])
        status = await self.tcset_param(param_names=['loss'])
        #assert False

    @pytest.mark.asyncio
    async def test_tcsee_delay_n_dublicate_upd(self):
        status = await self.tcset_param(param_names=['delay'])
        status = await self.tcset_param(param_names=['loss', 'update'])
        #assert False

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
        status = await self.tcset_param(param_names=['delay', 'rate', 'rate_unit'])
