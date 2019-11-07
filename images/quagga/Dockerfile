FROM alpine:3.4

RUN apk --no-cache add quagga iptables && \
	mkdir /var/log/zebra && \
    chown -R quagga:quagga /var/log/zebra && \
    chown -R quagga:quagga /var/run/quagga


ENTRYPOINT sh /etc/quagga/start.sh
