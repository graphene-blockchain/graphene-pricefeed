FROM python:3.9

WORKDIR /usr/src/app

COPY . .

RUN python3 setup.py install
RUN pip3 install .[history_db_postgresql]

VOLUME ["/conf", "/root/.local/share/bitshares"]

CMD [ "/usr/local/bin/graphene-pricefeed", "--configfile", "/config/config.yaml", "update" ]
