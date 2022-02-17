#!/bin/bash

apt install -y apache2 libapache2-mod-wsgi-py3 libapache2-mod-proxy-uwsgi libmysqlclient-dev libssl-dev python3-django redis-server python3-dev build-essential apt-get install net-tools python3-pip git

pip3 install mysqlclient aredis tornado websocket-client channels==3.0.4 channels_redis django_redis requests