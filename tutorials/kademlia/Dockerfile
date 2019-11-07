FROM madt/client

RUN pip3 install kademlia

COPY ./kademlia_tester.py kademlia_tester.py

CMD python kademlia_tester.py $KADEMLIA_ARGS



