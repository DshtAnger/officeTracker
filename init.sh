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

#locale-gen zh_CN.utf8
#cp /etc/apache2/envvars /etc/apache2/envvars.old
#sed -i "s/export LANG=C/#export LANG=C/g" /etc/apache2/envvars
#sed -i "s/export LANG/#export LANG/g" /etc/apache2/envvars
#echo "export LANG=zh_CN.utf8" >> /etc/apache2/envvars
#source /etc/apache2/envvars

a2dissite officeTracker
service apache2 reload
a2ensite officeTracker
service apache2 reload