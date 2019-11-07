import asyncio
import sys
import uuid

from kademlia.network import Server
from madt_client import MADT_Client

wait_for = asyncio.get_event_loop().run_until_complete

node = Server() # seting Kademlia server up
wait_for(node.listen(8080)) # port 8080 is used across all nodes
if len(sys.argv) > 1:  
    # Tester will try to bootstrap kademlia with any ip address passed as a
    # argument. Bootstraping nodes have to wait until nodes they're trying to 
    # connect are up, since all nodes start work at the same time
    wait_for(asyncio.sleep(3)) 
    wait_for(node.bootstrap([(ip, 8080) for ip in sys.argv[1:]])) 
else:
    wait_for(asyncio.sleep(5)) # wait untill other nodes will bootstrap

madt_client = MADT_Client()

status = '1'
log = ''
while True: # Main Testing Loop
    wait_for(asyncio.sleep(1))
    try:
        key = uuid.uuid4().hex
        value = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua"
        # Saving data. Kademlia's node.set will return False if it can't save data,
        # in this case we'll send status=1 to the madt monitoring system and node  
        # on the graph will turn red
        log = 'setting key = ' + key
        status = '1'
        if not wait_for(node.set(key, value)):
            madt_client.send(status, log, len(node.storage.data))
            continue

        # If we've managed to successfully save data, we need to load it and compare in 
        # order to completelly test functionality of Kademlia. node.get will return False 
        # on failure,in this case we'll send status=2 to the madt monitoring system and   
        # node on the graph will turn yellow
        log += '\n' + 'getting key'
        status = '2'
        ret_val = wait_for(node.get(key))
        if not ret_val:
            madt_client.send(status, log, len(node.storage.data), len(node.storage.data))
            continue
        # Comparing initial and retrieved value, sending status=3 if they're different
        # and status=0, if everything is OK. This will turn node on graph violet or green
        # respectively.
        log += '\n' + 'comparing values'
        if value != ret_val:
            madt_client.send('3', log + '\nwrong value', len(node.storage.data))
        else:
            madt_client.send('0', log + '\nsuccess', len(node.storage.data))
        
            
    except Exception as e:
        # If any sort of exception was raised, it'll be sent in the text log alongside 
        # with the last recorded status
        madt_client.send(status, log + '\n' + str(e), len(node.storage.data))
        print(e)
        continue
