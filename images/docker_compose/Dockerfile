FROM docker:dind

RUN apk add py-pip \
            python-dev \
            libffi-dev \
            openssl-dev \
            gcc \
            libc-dev \
            make \
            iproute2 \
            iptables && \
            pip install docker-compose

ADD wait_docker.sh /wait_docker.sh

ENV DOCKER_HOST=unix:///var/run/docker.sock

WORKDIR /app

CMD dockerd-entrypoint.sh > /docker.log 2>&1 & \
           sh /wait_docker.sh && docker-compose up;
