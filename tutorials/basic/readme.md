To run:

1. Download and start MADT
```
cd ~
git clone --recursive https://github.com/dltcspbu/madt/
mkdir ~/madt/labs && export MADT_LABS_DIR=$HOME/madt/labs
mkdir ~/madt/sockets && export MADT_LABS_SOCKETS_DIR=$HOME/madt/sockets

cd madt
sudo pip3 install -r ./requirements.txt
sudo make && sudo make install

sudo -HE env PYTHONPATH=$HOME/madt:$PYTHONPATH SSH_PWD=demo python3 madt_ui/main.py 80  
```

2. Build images and start the lab
```
#open new terminal window
cd ~/madt
cd ./tutorials/basic
docker pull inutano/wget
docker build madt/nginx .
python3 ./lab.py
```

3. Open 127.0.0.1:80
4. login as `demo:demo`
5. Open lab ![image](https://user-images.githubusercontent.com/2915361/76143162-fe747180-606c-11ea-8b50-429b9067c62b.png)
6. Observe graph ![image2](https://user-images.githubusercontent.com/2915361/76143179-2368e480-606d-11ea-8d11-8ce5d360884e.png)

