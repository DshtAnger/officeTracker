# coding=utf-8

import requests
import json
import django
import os
import sys
import time
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'officeTracker.settings')
django.setup()

from server.models import CompanyIp

Cookie = sys.argv[1]

csrf_token = sys.argv[2]

UA = {
'Accept': 'application/json, text/plain, */*',
'Accept-Encoding': 'gzip, deflate',
'Accept-Language': 'zh-CN,zh;q=0.9',
'Connection': 'keep-alive',
'Content-Type': 'application/json;charset=UTF-8',
'Cookie': Cookie,
'Host': 'v2.polaris.oa.com',
'Origin': 'http://v2.polaris.oa.com',
'Referer': 'http://v2.polaris.oa.com/',
'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
'x-csrf-token': csrf_token
}


url = 'http://v2.polaris.oa.com/api/proxy'


ip_list = []

for i in range(2):

    payload = {"params": {
        "url": "/naming/v1/instances?namespace=Production&service=OA-DevCloud-Internet-IP&offset=%s&limit=100" % (i*100),
        "method": "get"}}

    response = requests.post(url, headers=UA, data=json.dumps(payload))

    if response.status_code == 200:

        data = json.loads(response.text).get('data')
        data = data.get('instances') if data else None

        if data:
            for item in data:
                ip = item.get('host')
                city = item.get('location').get('zone')
                region = item.get('location').get('region')
                campus =  item.get('location').get('campus')
                if '/' in ip:
                    type = 'subnet'
                else:
                    type = 'host'

                if ip == '58.56.129.144/27':
                    ip = '58.56.129.144'

                ip_list.append({'ip':ip, 'city':city, 'type':type, 'region':region, 'campus':campus, 'update_time':timezone.now()})

update_count = 0
add_count = 0
delete_count = 0

# 每次运行程序,把库中所有ip信息未变更的条目、更新update_time到最新时间，把不存在的ip条目添加进数据库
for ip in ip_list:
    try:
        ip_obj = CompanyIp.objects.get(ip=ip.get('ip'))
        ip_obj.update_time = ip.get('update_time')
        ip_obj.save()
        update_count += 1
    except CompanyIp.DoesNotExist:
        CompanyIp.objects.create(ip=ip.get('ip'), type=ip.get('type'), city=ip.get('city'), region=ip.get('region'), campus=ip.get('campus'), update_time=ip.get('update_time'))
        add_count += 1

# 每次运行程序，在更新数据库后，把所有update_time早于今天的条目删除（意味着这些条目被数据源删除了）
for ip_obj in CompanyIp.objects.all():
    if (timezone.now() - ip_obj.update_time).days > 0:
        ip_obj.delete()
        delete_count += 1

print(f'[{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}] add_count: {add_count}, update_count: {update_count}, delete_count: {delete_count}')