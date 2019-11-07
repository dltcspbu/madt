FROM python:3-alpine

RUN apk add -U gcc \
	       musl-dev \
	       python3-dev \
	       linux-headers \
	       zeromq-dev \
	       iproute2 \
	       iptables && \
    pip3 install requests pyzmq

ADD ./lib /etc/madt/madt_client

ENV PYTHONPATH=/etc/madt:$PYTHONPATH
