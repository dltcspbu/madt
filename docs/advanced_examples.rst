
Advanced examples
=================

This section of documentation contains highly specific examples that aren't
suitable for introduction, but will be useful nevertheless.

Docker compose
--------------

If you’re using docker-compose to deploy your application you can launch the all containers
on a single node using madt/docker_compose image. This image is not built by default,
so you have to build it manually: ::

    cd ~/images/docker_compose
    docker build -t madt/docker_compose .

Nodes that use this image will require several additional options to work properly.
First of all, nodes must be launched in privileged mode. Besides that, if docker-compose
will have to pull images from the Docker Hub, the internet connection should be enabled with
the enable_internet parameter.

In this example,  we'll use a model from the dynamic routing tutorial to demonstrate the use of
docker-compose in the MADT. Instead of Nginx server we will use Nginx proxy and a simple whoami
webserver launched together with docker-compose. Here is  our docker-compose.yml:

.. literalinclude:: ../tutorials/docker_compose/docker-compose.yml
    :language: yaml

We have to change model definition script to use docker compose on the server and
set additional host resolving rule on clients:

.. literalinclude:: ../tutorials/docker_compose/lab.py

Since Nginx proxy routes requests using Host field value, we’re using extra_host parameter
from the `Docker Python API <https://docker-py.readthedocs.io/en/stable/containers.html#docker.models.containers.ContainerCollection.run>`_
to set hostname for the server without proper DNS.

After creating files for the new model and launching it, you can use the monitoring interface
to see status messages from the nodes. Docker-compose will require some time to launch
the application, so client nodes won’t be able to establish a connection with the server.
This will make nodes change color to purple in the monitoring interface. When compose
will finish preparations, the server will start sending replies to clients and the color of
the nodes will turn green.


Kademlia
--------

Let's consider the following example:

Numerous autonomous sensors are spread over a large area. They do not have internet access,
however, they’re connected to an isolated local area network. Developers want to use
DHT Kademlia to organize distributed storage of sensor readings. In theory, this should facilitate
data collection and ensure that some of the readings are retained even if the sensor is damaged.

We will use madt to find the minimum requirements for the local network that will ensure that every
sensor reading taken every N minutes will be stored in DHT before the next reading arrives.

To simulate sensors via MADT we must implement a program that generates data and writes it to DHT
every N seconds. Besides that, it sends the current state to the MADT monitoring subsystem via
madt_client.

.. literalinclude:: ../tutorials/kademlia/kademlia_tester.py

MADT uses docker containers to effectively simulate a fully isolated environment for each computer
in the simulated network. Because of that, we have to create a Docker image with all dependencies for
our pseudo-sensor (such as madt_client and kademlia).

.. literalinclude:: ../tutorials/kademlia/Dockerfile
    :language: dockerfile

Now that our application is ready for testing, we can proceed to describe the structure of the virtual
network on top of which the application will be launched. To do this, MADT provides a Python API available
in the :py:mod:`madt_lib` module. Since all sensors are connected to the same local network, the structure
of the virtual network will be as simple as possible. The following Python script creates a network model
and saves it in the /app/labs/tutorial folder:

.. literalinclude:: ../tutorials/kademlia/lab.py

After running the script, the model is ready for testing.

To automate this process, we’ll use another python script that runs the model’s instances.
Each successive instance will have higher network latency until Kademlia will fail to save readings in time:

.. literalinclude:: ../tutorials/kademlia/run_test.py

After the delay in the network will make Kademlia DHT too slow to save values in time,
the script will alert you and exit.
