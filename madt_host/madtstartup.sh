#!/usr/bin/env ash

# $DOCKER_PORT
# $SSH_PORT
# $MADT_SERVER
# $MADT_UI_PORT
# $MADT_FRPS_PORT

envsubst < frpc.template.ini > frpc.ini;

frp/frpc -c frpc.ini &
/usr/sbin/sshd -E ssh.log;

curl -d "name=$HOSTNAME&docker_port=$DOCKER_PORT&ssh_port=$SSH_PORT" http://$MADT_SERVER:$MADT_UI_PORT/connect > /root/.ssh/authorized_keys;

sh /images/build.sh &

dockerd-entrypoint.sh
