#!/bin/bash

# 手工添加环境变量,~/.profile,/etc/apache2/envvars

mkdir ./upload
mkdir ./download

sh ./install_requirements.sh

sed -i "s/DEBUG = True/DEBUG = False/g" ./officeTracker/settings.py

python3 ./manage.py makemigrations
python3 ./manage.py migrate

chmod 755 -R ../
chown www-data:www-data -R ./upload/
chown www-data:www-data -R ./download/


#locale-gen zh_CN.utf8
#cp /etc/apache2/envvars /etc/apache2/envvars.old
#sed -i "s/export LANG=C/#export LANG=C/g" /etc/apache2/envvars
#sed -i "s/export LANG/#export LANG/g" /etc/apache2/envvars
#echo "export LANG=zh_CN.utf8" >> /etc/apache2/envvars
#source /etc/apache2/envvars


sed -i "s/ServerName XXX/ServerName ${HOST_SERVER}/g" ./officeTracker.conf
cp ./officeTracker.conf /etc/apache2/sites-available

a2enmod proxy
a2enmod proxy_http
a2enmod proxy_wstunnel

a2dissite officeTracker
service apache2 reload
a2ensite officeTracker
service apache2 restart



check_upload_server=`ps aux | grep "http.server --bind 0.0.0.0" | grep -v grep`
check_ws_server=`ps aux | grep "daphne officeTracker.asgi:application -b 0.0.0.0 -p 8888" | grep -v grep`

if  [[ $check_upload_server =~ "http" ]]
then
  echo "upload_server had started."
else
  nohup python3 -u -m http.server --bind 0.0.0.0 8080 --directory /root/officeTracker/upload/ >> /root/officeTracker/upload.log 2>&1 &
  echo "upload_server start Done."
fi

if [[ $check_ws_server =~ "daphne" ]]
then
  echo "ws_server had started."
else
  nohup python3 -u /usr/local/bin/daphne officeTracker.asgi:application -b 0.0.0.0 -p 8888 >> /root/officeTracker/ws.log 2>&1 &
  echo "ws_server start Done."
fi