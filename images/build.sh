
until [ -e '/var/run/docker.sock' ]; do echo "waiting for docker..."; sleep 3; done;

SCRIPTPATH="$( cd "$(dirname "$0")" ; pwd -P )"

docker build -t madt/base $SCRIPTPATH/base && printf "\n\tBase ready\n\n";

docker build -t madt/client $SCRIPTPATH/madt_client && printf "\n\tClient ready\n\n";

docker build -t madt/quagga $SCRIPTPATH/quagga && printf "\n\tQuagga ready\n\n";
