from peewee import *
import docker
from .config import prefix

db = SqliteDatabase('madt.sqlite', pragmas={'foreign_keys': 1})


class BaseModel(Model):
    class Meta:
        database = db


class Host(BaseModel):
    name = TextField()
    address = TextField()
    docker_port=IntegerField()
    ssh_port=IntegerField()
    is_alive = BooleanField(default=False)
    protocol= TextField()

    def get_docker_client(self):

        if self.protocol == 'tcp':
            url = '{0}://localhost:{1}'.format(self.protocol, self.docker_port)
        else:
            url = '{0}://{1}'.format(self.protocol, self.address)

        return docker.DockerClient(base_url=url)

    @classmethod
    def get_all_configs(cls):
        return {h.name: h.get_config() for h in cls.select()}

    def get_config(self):
        return {
            'id': self.id,
            'address': self.address,
            'docker_port': self.docker_port,
            'ssh_port': self.ssh_port,
            'protocol': self.protocol
        }


class Lab(BaseModel):
    name = TextField()
    runtime = TextField()

    def list_containers(self):
        if self.runtime == 'cluster':
            containers = []
            hosts = self.get_hosts()
            for host in hosts:
                print('[ get containers ]', host.name)
                host_containers = host.get_docker_client().containers.list(filters={'name': prefix(self.name)})
                containers.extend(host_containers)
            # TODO: fix this goddamit, sql is the last thing I want to mess with right now, but this is ugly
            return list(set(containers))
        else:
            return docker.from_env().containers.list(filters={'name': prefix(self.name)})

    def get_hosts(self):
        return Host.select().join(Node).where(Node.lab_id == self.id)

    def get_host_map(self):
        hosts = self.get_hosts()
        hosts.prefetch(Node)
        hosts.prefetch(Network)

        return {h.name: {
                'nodes': [n.name for n in h.nodes],
                'networks': [n.name for n in h.networks]
        } for h in hosts}


class Node(BaseModel):
    name = TextField()
    lab = ForeignKeyField(Lab, backref='nodes', on_delete='CASCADE')
    host = ForeignKeyField(Host, backref='nodes', on_delete='CASCADE')
    short_id = TextField()


class Network(BaseModel):
    name = TextField()
    lab = ForeignKeyField(Lab, backref='networks', on_delete='CASCADE')
    host = ForeignKeyField(Host, backref='networks', on_delete='CASCADE')


if __name__ == "__main__":
    db.connect()
    try:
        db.drop_tables([Host, Lab, Node, Network])
    except:
        pass
    db.create_tables([Host, Lab, Node, Network])
    # TODO: Host.create(name='local', protocol='unix', address='/var/run/docker.sock', is_alive=True)
    db.close()

