from django.shortcuts import render

# Create your views here.

from django.http import Http404,HttpResponse,HttpResponseRedirect,FileResponse
from django.utils import timezone
from django_redis import get_redis_connection
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django import forms
from server.models import *
import requests
import json
import hashlib
import random
import time
import re
import os
import shutil
import traceback

redis = get_redis_connection()
VALID_CHARS = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'

SESSION_EXPIRY_TIME = 60 * 60

WHITELIST = json.loads(os.getenv('WHITELIST'))

WORK_SERVER = json.loads(os.getenv('WORK_SERVER'))

def ip_filter(ip,match_segment):
    ip_segment = '.'.join(ip.split('.')[:match_segment])
    for white_ip in WHITELIST:
        white_ip_segment = '.'.join(white_ip.split('.')[:match_segment])
        if ip_segment == white_ip_segment:
            return True
    return False

def randbytes(n):
    return ''.join([chr(random.randint(1, 127)) for _ in range(n)])

def sha256(string):
    return hashlib.sha256(string.encode('utf-8')).hexdigest()

def cala_file_hash(upload_file_obj):
    file_hash = hashlib.sha256()
    for chunk in upload_file_obj.chunks():
        file_hash.update(chunk)
    return file_hash.hexdigest()

def cala_watermark(file_hash,upload_ip,upload_time,random_8byte):
    return sha256(file_hash + upload_ip + upload_time + random_8byte)

def timezone_to_string(date):
    return date.strftime("%Y-%m-%d %H:%M:%S")

def get_current_time():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

def handle_uploaded_file(upload_file_obj, upload_file_path):
    with open(upload_file_path, 'wb+') as local_file_obj:
        for chunk in upload_file_obj.chunks():
            local_file_obj.write(chunk)

def get_valid_filename(s):
    return re.sub(r'(?u)[^-\w.]', '_', s)

class UserForm(forms.Form):
    user_id = forms.CharField(max_length=32)
    user_passwd = forms.CharField(max_length=64)
    user_submit = forms.CharField(max_length=16)

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

    def clean_user_submit(self):
        user_submit = self.cleaned_data['user_submit']
        if user_submit not in ['submit-login','submit-register']:
            raise forms.ValidationError("submit type is illegal.")
        else:
            return user_submit


def login(request):

    current_ip = request.META['REMOTE_ADDR']
    if not ip_filter(current_ip, 3):
        raise Http404()

    context = {}
    if request.method == "POST":
        uf = UserForm(request.POST)
        if uf.is_valid():

            user_id = uf.cleaned_data['user_id']
            user_passwd = uf.cleaned_data['user_passwd']
            user_submit = uf.cleaned_data['user_submit']

            if user_submit == 'submit-register':

                try:
                    User.objects.get(user_id=user_id)
                    context['points_info'] = ['The RTX id has been registered.']
                    return render(request,'login.html',context)
                except User.DoesNotExist:
                    User.objects.create(user_id=user_id, user_passwd=user_passwd, user_ip=current_ip)
                    context['points_info'] = ['Registered successfully, please login.']
                    return render(request, 'login.html', context)

            elif user_submit == 'submit-login':

                try:
                    user_obj = User.objects.get(user_id=user_id)
                    if user_passwd == user_obj.user_passwd:

                        request.session['user_id'] = user_id
                        request.session['is_login'] = True
                        request.session['login_ip'] = current_ip
                        request.session['secret'] = sha256(user_id+user_passwd+current_ip)
                        request.session.set_expiry(SESSION_EXPIRY_TIME)

                        response = HttpResponseRedirect('/index')
                        #context['points_info'] = ['Login successfully.']
                        return response
                    else:
                        context['points_info'] = ['Password error.']
                        return render(request, 'login.html', context)

                except User.DoesNotExist:
                    context['points_info'] = ['The RTX id is not registered, please register first.']
                    return render(request, 'login.html', context)

        else:
            context['points_info'] = uf.errors.values
    else:
        if request.session.get("is_login", None):
            return HttpResponseRedirect('/index')
        else:
            context['points_info'] = ["Please login after registration using RTX id."]

    return render(request,'login.html',context)

def logout(request):

    if not ip_filter(request.META['REMOTE_ADDR'], 3):
        raise Http404()

    if request.session.get("is_login", None):
        request.session.flush()
        return HttpResponseRedirect('/login')
    else:
        return HttpResponse('No login')

def index(request):

    if not ip_filter(request.META['REMOTE_ADDR'], 3):
        raise Http404()

    context = {}
    context['data'] = []
    if request.session.get("is_login", None):
        user_id = request.session['user_id']

        file_obj = File.objects.filter(user_id=user_id).order_by('-upload_time')

        for one_obj in file_obj:

            track_obj = Track.objects.filter(file_watermark=one_obj.file_watermark).order_by('-access_time')
            track_obj_data = [{'access_time': timezone_to_string(track.access_time), 'access_ip': track.access_ip} for track in track_obj]

            context['data'].append(
                {
                    'file_name': one_obj.file_name,
                    'file_size': one_obj.file_size,
                    'file_hash': one_obj.file_hash,
                    'upload_time': timezone_to_string(one_obj.upload_time),
                    'upload_ip': one_obj.upload_ip,
                    'download_file_path': one_obj.download_file_path,
                    'file_watermark': one_obj.file_watermark,
                    'track': track_obj_data
                }
            )

        context['user_id'] = user_id

        return render(request, "index.html", context)
    else:
        return HttpResponseRedirect('/login')

@csrf_exempt
def upload(request):

    if not ip_filter(request.META['REMOTE_ADDR'], 3):
        raise Http404()

    context = {}
    if request.session.get("is_login", None):
        user_id = request.session['user_id']
        upload_ip = request.session['login_ip']

        if request.method == 'POST':
            #file = request.FILES.get('upload_file', None) #form提交场景，get from表单里input标签的name,这个name在构造js formData apped时指定key

            files = request.FILES.getlist('file[]', None) #jQuery提交场景，request.FILES == <MultiValueDict: {'file': [<InMemoryUploadedFile: 05241946734744.jpg (image/jpeg)>]}>

            if not files:
                return HttpResponse('No file uploaded.')

            result = []
            for file in files:

                print('origin file_name :',file.name)
                upload_valid_filename =  get_valid_filename(file.name)

                file_hash = cala_file_hash(file)
                upload_time = timezone.now()
                file_watermark = cala_watermark(file_hash, upload_ip, timezone_to_string(upload_time), randbytes(8))

                upload_file_path = f'{settings.BASE_DIR}/upload/{upload_valid_filename}'
                handle_uploaded_file(file,upload_file_path)

                try:
                    File.objects.create(user_id=user_id, user_owner=user_id, file_name=upload_valid_filename, file_size=file.size, file_hash=file_hash,
                                        upload_file_path=upload_file_path, upload_ip=upload_ip, upload_time=upload_time, file_watermark=file_watermark)
                except Exception:
                    exception_info = traceback.print_exc()
                    return HttpResponse(exception_info)

                #向redis下发任务
                task_index = random.randint(0,9)
                print('exec queue :',f'watermark_task{task_index}')

                task_data = {'file_watermark': file_watermark, 'task_time': timezone_to_string(upload_time), 'download_url':f'http://172.18.18.18:8080/{upload_valid_filename}' }
                redis.lpush(f'watermark_task{task_index}', json.dumps(task_data))

                result.append(f'{upload_valid_filename} uploaded successfully.')

            return HttpResponse('[OK]' + '\n'.join(result))
        else:
            return HttpResponseRedirect('/index')
    else:
        return HttpResponseRedirect('/login')


def download(request, file_watermark, file_name):

    if not ip_filter(request.META['REMOTE_ADDR'], 3):
        raise Http404()

    if request.session.get("is_login", None):
        #预留:后面要在下载时验证,下载人是否是该文件的共享人,要在session里额外添加身份信息

        file = open(f'{settings.BASE_DIR}/download/{file_watermark}/{file_name}', 'rb')
        response = FileResponse(file)
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = f'attachment;filename="{file_name}"'

        return response
    else:
        return HttpResponseRedirect('/login')


def notify(request,file_watermark):

    download_url = redis.hget(file_watermark, 'download_url')

    if download_url == None:
        return HttpResponse(f"No task {file_watermark}")
    else:
        download_url = download_url.decode('utf-8')

    file_name = download_url.split('/')[-1]
    download_file_path = f'{settings.BASE_DIR}/download/{file_watermark}/'

    try:
        rsp = requests.get(download_url)
        if rsp.status_code == 200:

            if not os.path.exists(download_file_path):
                os.mkdir(download_file_path)

            with open(download_file_path + file_name, 'wb') as f:
                f.write(rsp.content)

            file_obj = File.objects.get(file_watermark=file_watermark)
            file_obj.download_file_path = download_file_path + file_name
            file_obj.save()

            move_file = f'{settings.BASE_DIR}/upload/{file_name}'
            shutil.move(move_file, f'{settings.BASE_DIR}/move/')

            return HttpResponse(f"download watermarked file {file_name} finished.")

        elif rsp.status_code == 404:
            # 预留:无法下载到处理过的文档时，要重新给worker下发任务再次处理
            return HttpResponse(f"watermarked file {file_name} has been deleted.")
    except:
        return HttpResponse(f"download watermarked file {file_name} failed.")

def track(request,file_watermark):

    access_ip = request.META['REMOTE_ADDR']
    access_time = timezone.now()

    if not access_ip in WORK_SERVER:

        try:
            File.objects.get(file_watermark=file_watermark)
        except File.DoesNotExist:
            return Http404()

        Track.objects.create(file_watermark=file_watermark, access_ip=access_ip, access_time=access_time)

        return HttpResponse('')
    else:
        raise Http404()