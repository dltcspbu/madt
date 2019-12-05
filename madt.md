# Build madt image
```sh
docker build -t madt .
```


# Run docker container
```sh
sudo docker run --rm -it \
	--name madt --privileged \
	-p 8980:80 -p 8922:22 \
	-v ~/dltc/madt/labs:/home/demo/labs \
	-v ~/dltc/madt/madt_ui:/app \
	-e SSH_PWD=demo -e MADT_RUNTIME=docker \
  	--entrypoint ash madt
```

# Run next commands inside container
```sh
dockerd --oom-score-adjust 500 & sh /home/demo/images/build.sh

docker build -t madt/nginx /home/demo/tutorials/basic \
&& docker build -t madt/pyget /home/demo/tutorials/monitoring

cd /home/demo/tutorials/kademlia && sudo docker build -t kademlia .

cd /home/demo/examples && python3 kademlia_iterative.py /home/demo/labs/monitoring

cd /app

python3 main.py 80 -q
(or)
hypercorn main:app -b 0.0.0.0:80 -w 1
```

# Usage
Navigate to localhost:8990, use demo:demo credentials to login, go to monitoring, press restart
