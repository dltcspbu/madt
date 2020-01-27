FROM docker:dind
# FROM madt/kahypar

RUN apk add -U gcc \
               linux-headers \
               musl-dev \
               python3 \
               net-tools \
               iproute2 \
               python3-dev \
               linux-headers \
               zeromq-dev \
               curl \
               libffi-dev \
               openssl-dev \
               git \
               g++ \
               make \
               cmake \
               openssh 

# tc bugfix to allow delay distribution
RUN ln -s /usr/lib/tc /lib/tc

RUN mkdir -p ~/.ssh && \
    ssh-keygen -f ~/.ssh/id_rsa && \
    echo -e "Host *\n    StrictHostKeyChecking no" > ~/.ssh/config && \
    mkdir -p ~/frp && \
    wget -O - https://github.com/fatedier/frp/releases/download/v0.27.1/frp_0.27.1_linux_amd64.tar.gz | tar -xzf - \
        -C ~/frp --strip-components=1

RUN wget -O /usr/local/bin/ctop https://github.com/bcicen/ctop/releases/download/v0.7.2/ctop-0.7.2-linux-amd64 && \
    chmod +x /usr/local/bin/ctop && \
    mkdir -p /etc/madt && \
    touch /etc/madt/hosts && \
    touch /madt.log

WORKDIR /madt


ADD ./ /madt

ENV MADT_LABS_SOCKETS_DIR=/madt/sockets 
ENV MADT_LABS_DIR=/madt/labs

RUN ln -s /usr/lib/python3.7 /usr/lib/python3 && \
    touch ~/.bashrc && make && make install && \
    cp frps.ini /root/frp/frps.ini && \
    mkdir /etc/docker && \
    cp daemon.json /etc/docker/daemon.json

ENTRYPOINT dockerd --oom-score-adjust 500 --log-level debug > /docker.log 2>&1 & \
           if [[ "$MADT_RUNTIME" == "cluster" ]]; then \
               /root/frp/frps -c /root/frp/frps.ini > /root/frp/frp.log 2>&1 & \
           fi; \
           madt_ui 80
