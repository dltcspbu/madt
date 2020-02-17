import subprocess
import re
import sys
import time

from madt_client import MADT_Client

def ping(host):
    ret = subprocess.run(['ping', '-w', '1', '-c', '1', host],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT,
                         universal_newlines=True)

    if ret.returncode != 0:
        return False, ret.stdout
    else:
        match_groups = re.search(r'time=(\d+\.\d+) ms', ret.stdout).groups()

        return (float(match_groups[0]) if len(match_groups) > 0 else False), ret.stdout

if len(sys.argv) != 2:
    print("Usage: python3 pinger.py [ ip_list file name]")
    exit(1)

config_filename = sys.argv[1]
with open(config_filename) as config_file:
    ip_list = [line.strip() for line in  config_file.readlines() if line.strip()]

if not ip_list:
    exit(1)

madt_client = MADT_Client()

while True:
    for ip in ip_list:
        time.sleep(1)
        try:
            ping_time, log = ping(ip)
            if ping_time:
                madt_client.send('0', log, int(ping_time*10))
            else:
                madt_client.send('1', log, 0)

        except Exception as e:
            madt_client.send('3', str(e), 0)
