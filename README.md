# MADT - a distributed application modeling system

Main features of MADT:

* Realistic simulation of large scale IP networks,
* Deployment of a distributed application in the simulated network,
* Dynamic control over network conditions in individual sections of the simulated network,
* Real-time visualization of the application state.

## Сore entities

The basic entity in MADT is a laboratory, a model of simulated network. 
To start a model MADT uses a minimal amount of information about virtual network structure and launch procedure of distributed application. 
This set of information also can be referred to as a model. MADT stores this information in the JSON-serialized file, lab.json. 

The simulated network is represented by graph. Nodes of this graph can be server, client, or router.
You can combine part of the network (a set of nodes) into a subnet and define rules for such subnet as well as configure the whole network. 

<img src="docs/_static/dynamic_routing.png" width="512">

## How to define the model

We use madt_lib Python API to configure a model. It provides four classes for defining a network model:

* madt_lib.Node represents network nodes. There are two types of nodes: routers and computers (PC). Routers provide dynamic routing of packets on the network and PCs host components of the tested application.
* madt_lib.Subnet represents IP subnetwork that connects a set of nodes.
* madt_lib.Overlay used to configure dynamic routing in the network. This is necessary for transferring data between computers from different subnets. 
* madt_lib.Network represents a wide or local area network. Each node, subnet or overlay of a network should be created only using its methods. A laboratory can have only one global network that can be used to create multiple local ones. 

## Docs

English docs: http://srv02.dltc.spbu.ru:8275/
Russian docs: http://srv02.dltc.spbu.ru:8276/

## Docker runtime
### Build sequence:
#### Server:

1. `docker build -t madt/kahypar images/kahypar`
2. `docker build -t madt .`

### Start sequence:
```bash
    docker run -d --privileged -p 8980:80 -p 8922:22 \
        -e SSH_PWD=demo \
        -e SSH_PWD=dltc \
        -e MADT_RUNTIME=docker madt
```


## Cluster runtime

Caution! Work in progress!

### Build sequence:

### Server:
For now, same as before. 

#### Host:
To build host image you'll need only `Dockerfile_image`, `madt_host`, `madt_client` and `images`  

1. `docker build -t madt/host -f Dockerfile_host .` 

### Start sequence:
#### Server
Since tinc daemons on hosts must connect to the server somehow, we're publishing wide range of 
ports for server's tinc daemon to use. Port publication must map the to the same ports on host. 
However, it's possible to change port range used by changling `PORT_RANGE` variable in cluster 
runtime.
```bash
   docker run -it -m 10GB --privileged --runtime kata-runtime --name madt \  
        -v ~/madt/labs:/home/demo/labs \
        -p 9080:80 -p 9022:22 -p 9077:7000 \ 
        -p 9100-9200:9100-9200 \
        -e SSH_PWD=demo \
        -e MADT_SERVER_ADDRESS=40.112.66.112 madt:test
```

#### Host
Note that before starting host you must make sure that both docker and ssh port are vacant on server.
`MADT_UI_PORT` and `MADT_FRPC_PORT` correspond to published 80 and 7000 port of the server.  
```bash
    docker run --privileged -it --name madt  \
        -e MADT_SERVER=40.112.66.112 \
        -e MADT_UI_PORT=9080 \
        -e MADT_FRPS_PORT=9077 \
        -e SSH_PORT=9201 \   
        -e DOCKER_PORT=9202 madt/host:test
```
