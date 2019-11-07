import os

prefix = lambda name: 'MADT_' + str(name) + '_'

labs_dir = os.path.abspath(os.path.join(os.getcwd(), 'labs')) if 'MADT_LABS_DIR' not in os.environ \
    else os.environ['MADT_LABS_DIR']

lab_path = lambda name: os.path.join(labs_dir, name)
