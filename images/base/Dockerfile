FROM alpine

# ADD ./test-startup.sh /startup.sh

# RUN chmod +x /startup.sh

RUN apk --no-cache add fping iproute2 iptables

ENTRYPOINT ["tail", "-f", "/dev/null"]
