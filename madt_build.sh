#!/usr/bin/ash

for lastarg; do true; done
lastarg=$(realpath $lastarg)
echo "Build dir: $lastarg"

tmpdir="/tmp/madt/$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 15;)"
echo "tmpdir on all servers: $tmpdir"

for p in $(cat /etc/madt/hosts); do
    echo "Going to $p";
    echo "Making tmpdir";
    ssh -p $p root@localhost "mkdir -p $tmpdir";

    echo "Copying tmpdir";
    scp -P $p -r $lastarg/* root@localhost:$tmpdir;

    echo "Building";
    ssh -p $p root@localhost "cd $tmpdir && /usr/local/bin/docker build $@";
    echo "Done";
done </etc/madt/hosts