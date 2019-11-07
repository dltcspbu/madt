import math
import os
import json
from tarfile import TarFile, TarInfo
import io
from ipaddress import IPv4Address
import base64

class DynamicTar(TarFile):
    """Helper class to simplify addition of dynamically generated
        files to the docker container"""
    def __init__(self, fileobj=None):
        TarFile.__init__(
            self,
            fileobj=fileobj if fileobj is not None else io.BytesIO(),
            mode='w')

    def send_to_container(self, container, dest_path):
        self.fileobj.seek(0)
        return container.put_archive(dest_path, self.fileobj.read())

    def to_base64(self):
        self.fileobj.seek(0)
        return base64.b64encode(self.fileobj.read()).decode()

    @classmethod
    def from_dir(cls, source_path, dir_arcname=None):
        self = cls()
        source_path = os.path.abspath(source_path)
        if dir_arcname is None:
            dir_arcname = os.path.basename(source_path)

        for file in os.listdir(source_path):
            self.add(os.path.join(source_path, file),
                     arcname=os.path.join(dir_arcname, file))

        return self

    @classmethod
    def from_str(cls, filename, string):
        self = cls()

        b_str = string.encode('utf-8')

        info = TarInfo(filename)

        fileobj = io.BytesIO()
        info.size = fileobj.write(b_str)
        fileobj.seek(0)

        self.addfile(tarinfo=info, fileobj=fileobj)

        return self

    @classmethod
    def from_base64(cls, string):
        b_str = base64.b64decode(string)
        fileobj = io.BytesIO()
        fileobj.write(b_str)

        return cls(fileobj=fileobj)






def ceil_power_of_2(x):
    return math.ceil(math.log(x) / math.log(2))


def load_lab_config(lab_path):
    lab_path = os.path.realpath(lab_path)

    with open(os.path.join(lab_path, 'lab.json'), 'r') as config_file:
        return json.load(config_file)


def is_private(ip):
    return IPv4Address(ip).is_private







