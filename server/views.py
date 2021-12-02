from django.shortcuts import render

# Create your views here.

from django.http import HttpResponse

import requests
import os
from redis import StrictRedis
redis = StrictRedis(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'), password=os.getenv('REDIS_PASSWORD'))


def index(request,file_watermark="123"):

    return HttpResponse(f"Hello, world. file_watermark: {file_watermark}")

def notify(request,file_watermark):

    download_url = redis.hget(file_watermark, 'download_url').decode('utf-8')

    file_name = download_url.split('/')[-1]
    file_path = f'/root/download/{file_watermark}/'
    if not os.path.exists(file_path):
        os.mkdir(file_path)

    try:
        rsp = requests.get(download_url)
        with open(file_path+file_name, 'wb') as f:
            f.write(rsp.content)
        return HttpResponse(f"download watermarked file finished.")
    except:
        return HttpResponse(f"download watermarked file failed.")

