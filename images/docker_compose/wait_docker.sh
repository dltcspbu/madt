#!/bin/sh
until [ -e '/var/run/docker.sock' ]; do echo "waiting for docker..."; sleep 3; done;