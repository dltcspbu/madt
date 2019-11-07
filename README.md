## Docker runtime
### Build sequence:
#### Server:

1. `docker build -t madt/kahypar images/kahypar`
2. `docker build -t madt .`

### Start sequence:
```bash
    docker run -d --privileged -p 8980:80 -p 8922:22 
        -e SSH_PWD=demo 
        -e SSH_PWD=dltc 
        -e MADT_RUNTIME=docker madt
```


## Cluster runtime
### Build sequence:

### Server:
For now, same as before. 

#### Host:
To build host image you'll need only `Dockerfile_image`, `madt_host`, `madt_client` and `images`  

1. `docker build -t madt/host -f Dockerfile_host .` 

### Start sequence:
#### Server

FIXME

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
