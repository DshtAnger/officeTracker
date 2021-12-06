from django.shortcuts import render

# Create your views here.

from django.http import HttpResponse,HttpResponseRedirect
from django_redis import get_redis_connection
from django import forms
from server.models import *
import requests
import os

redis = get_redis_connection()
VALID_CHARS = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'

class UserForm(forms.Form):
    user_id = forms.CharField(max_length=32)
    user_passwd = forms.CharField(max_length=64)

    def clean_user_id(self):
        user_id = self.cleaned_data['user_id']

        if len(user_id) > 32:
            raise forms.ValidationError("password length error.")

        for i in user_id:
            if i not in VALID_CHARS:
                raise forms.ValidationError("There are illegal characters in RTX id.")

        return user_id

    def clean_user_passwd(self):
        user_passwd = self.cleaned_data['user_passwd']
        if len(user_passwd) != 64:
            raise forms.ValidationError("password length error.")
        else:
            return user_passwd


def index(request):
    context = {}
    current_ip = request.META['REMOTE_ADDR']
    if request.method == "POST":
        uf = UserForm(request.POST)
        if uf.is_valid():

            #注册提交信息合法，获取具体数据
            user_id = uf.cleaned_data['user_id']
            user_passwd = uf.cleaned_data['user_passwd']
            print(user_id,user_passwd)

            try:
                #检查该student_id是否已经注册.若已经注册，则重定向到登陆页面
                User.objects.get(user_id=user_id)
                #最后一位为0表明，若身份验证通过则提示是账号已注册
                response = HttpResponseRedirect('/login/?asi=')
                return response
            except User.DoesNotExist:
                User.objects.create(user_id=user_id,user_passwd=user_passwd,user_ip=current_ip)
                #最后一位为1表明，若身份验证通过则提示是账号注册成功
                #response = HttpResponseRedirect('/login/?asi='+redirect_args+'1')
                #return response
                context['points_info'] = '22222'
                render(request, 'login.html', context)
        else:
            context['points_info'] = uf.errors.values
    else:
        context['points_info'] = ["Please register first using your RTX id."]
        context['behaviour'] = "Login"

    return render(request,'login.html',context)


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