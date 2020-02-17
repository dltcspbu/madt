FROM madt/client

ADD pinger.py ./

RUN touch ip_list.conf

CMD python3 pinger.py ip_list.conf
