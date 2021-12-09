#!/bin/bash

apt install -y apache2 libapache2-mod-wsgi-py3 libmysqlclient-dev libssl-dev python3-django redis-server python3-dev build-essential

pip3 install mysqlclient aredis tornado