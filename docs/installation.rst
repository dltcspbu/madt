
Installation instructions
=========================

Most of this section describes the manual installation of the MADT system. However,
it’s better to launch MADT in docker container whenever possible, since it’s significantly
reduces deployment time. All you need to do to deploy MADT via docker is to use Dockerfile
provided with the system to build a Docker image: ::

    docker build -t madt .

Manual installation
-------------------

Before installing MADT, you need to install the system packages necessary for its operation.
Depending on the Linux distribution used, the package names may differ, this list is for Alpine Linux:

* cmake
* gcc
* linux-headers
* musl-dev
* python3
* python3-dev
* net-tools
* iproute2
* zeromq-dev
* tinc
* libffi-dev
* openssl-dev
* openssh
* curl

After installing the system packages, you need to install the necessary python3 modules: ::

    # sudo pip3 install tcconfig flask pyzmq peewee docker cryptography


Madt also needs Docker to work. Installation instructions are available in the `official docker documentation <http://docs.docker.com/install/>`_:
Besides that, the user who will be used to run the MADT components must be able to use Docker without sudo.
See `here <http://docs.docker.com/install/linux/linux-postinstall/>`_ for more details.

Now that all the MADT dependencies are installed, you can move on to the system itself.
First of all, it’s necessary to download MADT sources: ::

    git clone https://gitab.dltc.spbu.ru/DM/madt.git

Second step is to build helper docker images:

    sh images/build.sh

Then you need to make madt_lib python module available for import. There are two ways to do this:

* The first option is to move the module from the source directory to either one directories in
  which python searches for modules by default, for example:
  ``cp -r madt /usr/lib/python3.7/site-packages``
  Note that python module lookup path may vary from one environment to another.
* Second option is to add the madt source directory to the $PYTHONPATH environment variable:
  ``export PYTHONPATH=$PYTHONPATH:~/madt``
  However, you will have to do this every time you restart the system.

Next, you need to create directories to store the models and IPC sockets. ::

    mkdir -p labs
    mkdir -p sockets

After this step, the system is ready for operation.


MADT UI launch
--------------

Docker:
+++++++

``docker run -d --privileged --name madt -v ~/madt_labs:/app/labs -p [port]:80 madt``

Manual installation:
++++++++++++++++++++

.. code-block:: bash

    export LABS_DIR=~/madt/sockets
    export LABS_SOCKETS_DIR=~/madt/sockets
    cd ~/madt/madt_ui
    python3 main.py [ port ]

In both cases, [port] must be replaced with the port on which the WEB interface will be launched.





