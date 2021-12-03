from django.shortcuts import render

# Create your views here.

from django.http import HttpResponse
from django_redis import get_redis_connection
import requests
import os

redis = get_redis_connection()

def index(request,file_watermark='123'):
    context = {}
    context['points_info'] = ["Please register first ! And then login !",
                              "student id is pure digital less than 11 chars !"]
    context['behaviour'] = "Register"
    return render(request, 'base.html', context)

    #return HttpResponse(f"Hello, world. file_watermark: {file_watermark}")

def notify(request,file_watermark):

    download_url = redis.hget(file_watermark, 'download_url')

    if download_url == None:
        return HttpResponse(f"No task {file_watermark}")
    else:
        download_url = download_url.decode('utf-8')

    file_name = download_url.split('/')[-1]
    file_path = f'/root/download/{file_watermark}/'

    try:
        rsp = requests.get(download_url)
        if rsp.status_code == 200:

            if not os.path.exists(file_path):
                os.mkdir(file_path)

            with open(file_path+file_name, 'wb') as f:
                f.write(rsp.content)

            return HttpResponse(f"download watermarked file {file_name} finished.")

        elif rsp.status_code == 404:
            return HttpResponse(f"watermarked file {file_name} has been deleted.")
    except:
        return HttpResponse(f"download watermarked file {file_name} failed.")