import sys

sys.path

from madt_lib import runtime_api

def exit_with_usage():
    print('Usage: python3 madt.py [start|stop|restart] [ lab_path ] [ prefix ]')
    sys.exit(1)

if len(sys.argv) != 4:
    exit_with_usage()

command = sys.argv[1]
lab_path = sys.argv[2]
prefix = sys.argv[3]

if command not in ('start', 'stop', 'restart'):
    exit_with_usage()

f = getattr(runtime_api, command + '_lab')
print(f(lab_path, prefix))
