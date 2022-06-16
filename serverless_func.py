# -*- coding: utf8 -*-
import json
import time
import requests
import base64
import os

def main_handler(event, context):
    # print("Received event: " + json.dumps(event, indent = 2))
    # print("Received context: " + str(context))

    try:

        TRACK_SERVER = os.getenv('TRACK_SERVER')

        host = event['headers']['host']

        file_watermark = event['path'].split('/')[-1]
        access_ip = event['requestContext']['sourceIp']

        access_UA = event['headers'].get('user-agent')
        access_UA = access_UA if access_UA else event['headers'].get('User-Agent')

        print('host: {}\nfile_watermark: {}\naccess_ip: {}\naccess_UA: {}\nTime: {}'.format(host, file_watermark, access_ip, access_UA, time.time()))

        data = {
            'access_ip': access_ip,
            'access_UA': access_UA
        }

        args = base64.b64encode(json.dumps(data).encode('utf-8')).decode('utf-8')

        url = 'http://%s/track/%s/%s' % (TRACK_SERVER, file_watermark, args)

        requests.get(url)

        print('Requests Done.')

    except:
        pass

    return 1