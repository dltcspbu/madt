import madt_ui.main as main  # To be imported in a first line because of flask patch

import pytest
import docker
import requests
from quart import Quart
import asyncio
import json
import os
from madt_lib.network import Network
import peewee

import madt_ui
import madt_ui.config
from madt_ui import models
from madt_ui import net_control
from madt_ui.login import login
from madt_ui import lab_control
from madt_lib.runtime_api import restart_lab, stop_lab, start_lab
from madt_ui.models import Host, Lab, Node

app = main.app
dc = docker.from_env()


@pytest.fixture(name='madt_ui')
def _test_app():
    return app


server_image = 'madt/nginx'
client_image = 'inutano/wget'


class BasicLab:
    def lab_discription():
        net = Network('15.0.0.0/8')
        server = net.create_node('server', image=server_image)
        client = net.create_node('client', image=client_image,
                                 entrypoint='sh -c "while true; do wget -O - -T 3 $SERVER; sleep 1; done"')
        net.create_subnet('net', (server, client))
        net.configure(verbose=True)
        client.add_options(environment={'SERVER': server.get_ip()})
        net.render('labs/basic_lab', verbose=True)


class TestClass:
    def setup_method(self):
        self.passwd = 'demo'
        self.labname = 'basic_lab'

        os.environ["SSH_PWD"] = self.passwd
        os.environ["MADT_LABS_DIR"] = '/media/anna/DATA/dltc/madt_github/labs/'
        os.environ["MADT_LABS_SOCKETS_DIR"] = '/media/anna/DATA/dltc/madt_github/sockets/'

        self.test_client = app.test_client()
        self.server_img = dc.images.build(path='tutorials/basic/', tag=server_image)

    def teardown_module(self):
        self.container.remove(force=True)

    async def login(self):
        response = await self.test_client.post('/login', form={'username': 'demo', 'password': self.passwd})
        assert response.status_code == 302

    @pytest.mark.asyncio
    async def test_restart_lab(self):
        status_code = await self.login()
        print("status_code: ", status_code)
        status_code = BasicLab.lab_discription()
        response = await self.test_client.post('/lab/restart',
                                               json={'name': self.labname,
                                                     'tc_options': {}})

        assert response.status_code == 200
        test_images = [server_image + ":latest", client_image + ":latest"]
        try:
            lab = Lab.get(Lab.name == self.labname)
            containers = lab.list_containers()
            for cont in containers:
                if cont.image.tags[0] in test_images:
                    test_images.remove(cont.image.tags[0])
                else:
                    print("No such image: ", cont.image.tags[0], "\n")
                    assert False
            if test_images:
                print("List is not empty: More images were created!\n")
                assert False

        except peewee.DoesNotExist:
            print("No lab found\n")
            assert False
