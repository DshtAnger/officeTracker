#!/bin/bash

# 手工添加环境变量,~/.bashrc,/etc/apache2/envvars
source /root/.bashrc
source /etc/apache2/envvars
echo '[+] Enable Computing Resource Envs Done.'

sh ./install_requirements.sh
echo '[+] Install OS And Python Requirements Done.'

mkdir ./upload
mkdir ./download
chmod 755 -R ../
chown www-data:www-data -R ./upload/
chown www-data:www-data -R ./download/
echo '[+] Create Upload Download Folder And Configure Folder permissions Done.'

sed -i "s/DEBUG = True/DEBUG = False/g" ./officeTracker/settings.py
echo '[+] Close Project DEBUG Switch Done.'

python3 ./manage.py makemigrations
python3 ./manage.py migrate
echo '[+] Initialize Project Database Done.'

#locale-gen zh_CN.utf8
#cp /etc/apache2/envvars /etc/apache2/envvars.old
#sed -i "s/export LANG=C/#export LANG=C/g" /etc/apache2/envvars
#sed -i "s/export LANG/#export LANG/g" /etc/apache2/envvars
#echo "export LANG=zh_CN.utf8" >> /etc/apache2/envvars
#source /etc/apache2/envvars

sed -i "s/ServerName XXX/ServerName ${HOST_SERVER}/g" ./officeTracker.conf
cp ./officeTracker.conf /etc/apache2/sites-available
echo '[+] Configure Project Apache Conf File Done.'

a2enmod proxy
a2enmod proxy_http
a2enmod proxy_wstunnel
echo '[+] Enable Apache Proxy Module Done.'

a2dissite officeTracker
service apache2 reload
a2ensite officeTracker
service apache2 restart
echo '[+] Start Project Apache Server Done.'


check_upload_server=`ps aux | grep "http.server --bind 0.0.0.0" | grep -v grep`
check_ws_server=`ps aux | grep "daphne officeTracker.asgi:application -b 0.0.0.0 -p 8888" | grep -v grep`

if  [[ $check_upload_server =~ "http" ]]
then
  echo "[*] Upload Server Had Started."
else
  nohup python3 -u -m http.server --bind 0.0.0.0 8080 --directory /root/officeTracker/upload/ >> /root/officeTracker/upload.log 2>&1 &
  echo "[+] Upload Server Starts Done."
fi

if [[ $check_ws_server =~ "daphne" ]]
then
  echo "[*] Websocket Server Had Started."
else
  nohup python3 -u /usr/local/bin/daphne officeTracker.asgi:application -b 0.0.0.0 -p 8888 >> /root/officeTracker/ws.log 2>&1 &
  echo "[+] Websocket Server Starts Done."
fi

echo '[+] ALL Configurations Done.'