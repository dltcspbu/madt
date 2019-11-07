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
			   tinc \
			   htop \
			   libffi-dev \
			   openssl-dev \
			   git g++ make cmake && \
	pip3 install tcconfig \
				 flask \
				 quart \
                 pyzmq \
                 peewee \
                 cryptography \
                 flask-login

WORKDIR /app

RUN apk add openssh sudo nano && \
	ssh-keygen -f /etc/ssh/ssh_host_rsa_key -N '' -t rsa && \
	addgroup docker && \
	adduser -G docker -D demo && \
	echo "demo        ALL=(ALL)       NOPASSWD: ALL" >> /etc/sudoers

# tc bugfix to allow delay distribution
RUN ln -s /usr/lib/tc /lib/tc && \
	ln -s /images /home/demo/images
ENV LABS_SOCKETS_DIR=/sockets
# ENV LABS_DIR=/app/labs

RUN mkdir -p ~/.ssh && \
    mkdir -p ~/frp && \
    echo -e "Host *\n    StrictHostKeyChecking no" > ~/.ssh/config && \
    wget -O - https://github.com/fatedier/frp/releases/download/v0.27.1/frp_0.27.1_linux_amd64.tar.gz | tar -xzf - \
        -C ~/frp --strip-components=1 && \
    ssh-keygen -f ~/.ssh/id_rsa

ADD ./frps.ini /root/frp/frps.ini

ADD ./madt_ui /app
ADD ./madt_lib /home/demo/madt_lib

# compile .pyc and remove .py
RUN ln -s /home/demo/madt_lib /usr/lib/python3.7/site-packages/madt_lib && \
	python3 -m compileall -b /app && \
	find /app -name "*.py" -type f -delete && \
	python3 -m compileall -b /home/demo/madt_lib && \
	find /home/demo/madt_lib -name "*.py" -type f -delete && \
	chown -R demo /home/demo/madt_lib

ENV MADT_LABS_DIR=/home/demo/labs

ADD ./examples /home/demo/examples
ADD ./madt.py /home/demo/madt.py
ADD ./images /home/demo/images
# ADD ./ctop /usr/local/bin/ctop # pre-relase ctop
ADD ./daemon.json /etc/docker/daemon.json
ADD ./tutorials /home/demo/tutorials

RUN wget -O /usr/local/bin/ctop https://github.com/bcicen/ctop/releases/download/v0.7.2/ctop-0.7.2-linux-amd64 && \
    chmod +x /usr/local/bin/ctop && \
    mkdir /home/demo/labs && \
    mkdir -p /etc/madt && \
    touch /etc/madt/hosts && \
	touch /home/demo/madt.log && \
	cp -r /root/.ssh /home/demo/.ssh && \
	chown -R demo /home/demo  && \
	mkdir -p /sockets && \
	mkdir -p /etc/tinc


ENTRYPOINT echo "demo:$SSH_PWD" | chpasswd; \
           /usr/sbin/sshd -E /home/demo/ssh.log; \
   		   dockerd --oom-score-adjust 500 --log-level debug > /home/demo/docker.log 2>&1 & \
   		   (sh /home/demo/images/build.sh); \
   		   if [[ "$MADT_RUNTIME" == "cluster" ]]; then \
   		       /root/frp/frps -c /root/frp/frps.ini > /root/frp/frp.log 2>&1 & \
   		   fi; \
   		   if [[ -e main.py ]]; then \
		       echo "Starting uncompiled server"; \
			   python3 main.py 80 -q; \
           else \
			   echo "Starting compiled server"; \
			   python3 main.pyc 80  >> /home/demo/madt.log 2>&1; \
           fi
