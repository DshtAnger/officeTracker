#!/bin/bash

mkdir ./upload
mkdir ./download
mkdir ./move

sh ./install_requirements.sh

sed -i "s/DEBUG = True/DEBUG = False/g" ./officeTracker/settings.py

python3 ./manage.py makemigrations
python3 ./manage.py migrate

chmod 755 -R ../
chown www-data:www-data -R ./upload/
chown www-data:www-data -R ./download/
chown www-data:www-data -R ./move/

a2dissite officeTracker
service apache2 reload
a2ensite officeTracker
service apache2 reload