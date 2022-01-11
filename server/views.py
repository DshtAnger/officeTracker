from django.shortcuts import render

# Create your views here.

from django.http import Http404,HttpResponse,HttpResponseRedirect,FileResponse
from django.utils import timezone
from django.utils.encoding import escape_uri_path
from django_redis import get_redis_connection
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django import forms
from server.models import *
from django.db.models import Q
# import websocket
import requests
import json
import ipaddress
import hashlib
import random
import time
import re
import os
import shutil
import traceback

redis = get_redis_connection() # redis get出来的数据都是byte类型,使用前decode('utf-8')
VALID_CHARS = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'

SESSION_EXPIRY_TIME = 60 * 60

#WHITELIST = json.loads(os.getenv('WHITELIST','""'))

WHITELIST = [ ip_obj.ip for ip_obj in CompanyIp.objects.all()]

WORK_SERVER = json.loads(os.getenv('WORK_SERVER','""'))

HOST_SERVER = os.getenv('HOST_SERVER')

QUEUE_MAX = 10

ACCESS_INTERVAL = 2

def ip_filter(ip):
    if settings.DEBUG:
        return True
    for white_ip in WHITELIST:
        if ipaddress.ip_address(ip) in ipaddress.ip_network(white_ip):
            return white_ip
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

def show_file_size(size_str: int):
    #前端的文件大小限制，待做
    if 1024 <= size_str < 1024*1024:
        return '{:.2f} KB'.format(size_str/1024)
    elif 1024*1024 <= size_str <= 1024*1024*200:
        return '{:.2f} MB'.format(size_str /1024/1024)
    else:
        return '{0} B'.format(size_str)

def cala_watermark(file_hash, upload_ip, upload_time, user_id, random_8byte):
    return sha256(file_hash + upload_ip + upload_time + user_id + random_8byte)

def timezone_to_string(date):
    return date.strftime("%Y-%m-%d %H:%M:%S")

def get_current_time():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

def handle_uploaded_file(upload_file_obj, upload_file_path):
    with open(upload_file_path, 'wb+') as local_file_obj:
        for chunk in upload_file_obj.chunks():
            local_file_obj.write(chunk)

def get_valid_filename(origin_filename):
    return re.sub(r'(?u)[^-\w.]', '_', origin_filename)

# def send_websocket_data(user_id, ws_data):
#     try:
#         ws = websocket.WebSocket()
#         ws.timeout = 30
#
#         ws.connect(f'ws://{HOST_SERVER}/ws/{user_id}/')
#         ws.send(json.dumps(ws_data))
#
#         ws.close()
#
#     except Exception:
#         exception_info = traceback.format_exc()
#         print(exception_info)


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
    #user_agent = request.META['HTTP_USER_AGENT']
    current_ip = request.META['REMOTE_ADDR']
    if not ip_filter(current_ip):
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

    if not ip_filter(request.META['REMOTE_ADDR']):
        raise Http404()

    if request.session.get("is_login", None):
        request.session.flush()
        return HttpResponseRedirect('/login')
    else:
        return HttpResponseRedirect('/')

def index(request):

    if not ip_filter(request.META['REMOTE_ADDR']):
        raise Http404()

    context = {}
    context['file_data'] = []
    # context['self_data'] = []
    # context['sharer_data'] = []
    if request.session.get("is_login", None):
        user_id = request.session['user_id']

        file_obj = File.objects.filter(Q(user_id=user_id)|Q(file_sharer=user_id)).order_by('-upload_time')

        # #做分享人记录聚合时,需要考虑几种情况
        # # user_id是自己，且sharer也是自己的，为单独为自己上传场景,字段显示和之前全一样。不用管文件因素，因为每一条记录只会是一个文件。
        # file_obj_self = File.objects.filter(user_id=user_id, file_sharer=user_id).order_by('-upload_time')
        # # user_id是自己，但sharer都不是自己的，为给其他用户上传场景。一条显示中共享人字段把所有共享人包进去,下载链接为空,track展示多个人的记录。。要管文件因素，因为每个user_id可能对应了多个共享出去的文件
        # file_obj_sharer = File.objects.filter(user_id=user_id).filter(~Q(file_sharer=user_id))

        for one_obj in file_obj:

            track_obj = Track.objects.filter(file_watermark=one_obj.file_watermark).order_by('-access_time')
            track_obj_data = [{'access_time': timezone_to_string(track.access_time), 'access_ip': track.access_ip, 'access_UA':track.access_UA, 'access_city':track.access_city, 'access_legitimacy':track.access_legitimacy} for track in track_obj]

            context['file_data'].append(
                {
                    'file_name': one_obj.file_name,
                    'file_owner': one_obj.user_id,
                    'file_sharer': one_obj.file_sharer,
                    'file_size': one_obj.file_size,
                    'file_hash': one_obj.file_hash,
                    'upload_time': timezone_to_string(one_obj.upload_time),
                    'upload_ip': one_obj.upload_ip,
                    'download_file_path': one_obj.download_file_path if one_obj.file_sharer == user_id else 'None',
                    #ws有干扰，会导致刷新页面前用户看到下载按钮，要修改index页面。同时对下载api做cooki校验
                    'file_watermark': one_obj.file_watermark,
                    'track': track_obj_data
                }
            )

        # fille_sharer = ','.join([one.file_sharer for one in file_obj_sharer])
        # context['sharer_data'].append(
        #     {
        #         'file_name': one_obj.file_name,
        #         'file_owner': one_obj.user_id,
        #         'file_sharer': one_obj.file_sharer,
        #         'file_size': one_obj.file_size,
        #         'file_hash': one_obj.file_hash,
        #         'upload_time': timezone_to_string(one_obj.upload_time),
        #         'upload_ip': one_obj.upload_ip,
        #         'download_file_path': one_obj.download_file_path,
        #         'file_watermark': one_obj.file_watermark,
        #         'track': track_obj_data
        #     }
        # )


        user_data = User.objects.filter(~Q(user_id=user_id))
        context['user_data'] = [user.user_id for user in user_data]

        context['user_id'] = user_id

        return render(request, "index.html", context)
    else:
        return HttpResponseRedirect('/login')

@csrf_exempt
def upload(request):

    if not ip_filter(request.META['REMOTE_ADDR']):
        raise Http404()

    context = {}
    if request.session.get("is_login", None):
        user_id = request.session['user_id']
        upload_ip = request.session['login_ip']

        if request.method == 'POST':
            #file = request.FILES.get('upload_file', None) #form提交场景，get from表单里input标签的name,这个name在构造js formData apped时指定key

            files = request.FILES.getlist('file[]', None) #jQuery提交场景，request.FILES == <MultiValueDict: {'file': [<InMemoryUploadedFile: 05241946734744.jpg (image/jpeg)>]}>
            file_sharer = request.POST.get('file_sharer', None)

            if not files:
                return HttpResponse('No file uploaded.')

            if not file_sharer:
                file_sharer = user_id

            result = []
            for file in files:

                print('origin file_name :',file.name)
                upload_valid_filename =  get_valid_filename(file.name)

                file_hash = cala_file_hash(file)
                upload_file_path = f'{settings.BASE_DIR}/upload/{upload_valid_filename}'
                handle_uploaded_file(file, upload_file_path)

                try:
                    for sharer in file_sharer.split(','):

                        upload_time = timezone.now()
                        file_watermark = cala_watermark(file_hash, upload_ip, timezone_to_string(upload_time), sharer, randbytes(16))

                        File.objects.create(user_id=user_id, file_sharer=sharer, file_name=upload_valid_filename, file_size=show_file_size(file.size), file_hash=file_hash,
                                        upload_file_path=upload_file_path, upload_ip=upload_ip, upload_time=upload_time, file_watermark=file_watermark)

                        # 向redis下发任务,使用file_sharer标示要把下载链接展示给谁
                        task_index = random.randint(0, QUEUE_MAX - 1)
                        print('exec queue :', f'watermark_task{task_index}')

                        task_data = {'user_id': sharer, 'file_watermark': file_watermark,
                                     'task_time': timezone_to_string(upload_time),
                                     'download_url': f'http://172.18.18.18:8080/{upload_valid_filename}'}

                        redis.lpush(f'watermark_task{task_index}', json.dumps(task_data))

                        result.append(f'{upload_valid_filename} uploaded successfully.')

                except Exception:
                    exception_info = traceback.format_exc()
                    print(exception_info)
                    return HttpResponse('Create Error.')

            return HttpResponse('[OK]' + '\n'.join(result))
        else:
            return HttpResponseRedirect('/index')
    else:
        return HttpResponseRedirect('/login')


def download(request, file_watermark):

    if not ip_filter(request.META['REMOTE_ADDR']):
        raise Http404()

    if request.session.get("is_login", None):

        try:
            file_obj = File.objects.get(file_watermark=file_watermark)

            # 下载时验证身份,下载人是否是该文件的共享人,也就意味者归属人不能下载共享人的文件
            if file_obj.file_sharer != request.session.get("user_id", None):
                raise Http404()

        except File.DoesNotExist:
            raise Http404()

        output_filename = file_obj.download_file_path.split('/')[-1]

        file = open(file_obj.download_file_path, 'rb')
        response = FileResponse(file)
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = f'attachment;filename="{escape_uri_path(output_filename)}"'

        return response
    else:
        return HttpResponseRedirect('/login')


def notify(request,file_watermark):

    task_status = redis.hget(file_watermark, 'task_status').decode('utf-8')
    download_url = redis.hget(file_watermark, 'download_url')

    if task_status == False:

        file_obj = File.objects.get(file_watermark=file_watermark)
        file_obj.download_file_path = 'ERROR'
        file_obj.save()

        # 遗留工作:前端js通过is_success字段更新下载图标为x,前端模版根据download_file_path==None更新下载图标为x

        return HttpResponse(f"Failed task {file_watermark}. failed_info: {redis.hget(file_watermark, 'failed_info').decode('utf-8')}")

    elif download_url == None:
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

            # move_file = f'{settings.BASE_DIR}/upload/{file_name}'
            # shutil.move(move_file, f'{settings.BASE_DIR}/move/')

            # 通知前端进行下载图标状态更新
            # 由Win Worker在通知Server下载处理后文件的同时,访问用户websocket进行通知
            # send_websocket_data(file_obj.user_id, {'download_update':file_watermark})

            return HttpResponse(f"download watermarked file {file_name} finished.")

        elif rsp.status_code == 404:
            # 预留:无法下载到处理过的文档时，要重新给worker下发任务再次处理
            return HttpResponse(f"watermarked file {file_name} does not exist.")
    except:
        return HttpResponse(f"download watermarked file {file_name} failed.")

def track(request,file_watermark):

    access_ip = request.META['REMOTE_ADDR']
    access_time = timezone.now()
    access_UA = request.META['HTTP_USER_AGENT']

    try:
        if 'Mozilla/4.0 (compatible; ' in access_UA and access_UA[-1] == ')':
            access_UA = access_UA[25:-1]
    except:
        pass

    print(request.META['HTTP_USER_AGENT'])

    if not access_ip in WORK_SERVER:

        try:
            file_obj = File.objects.get(file_watermark=file_watermark)
        except File.DoesNotExist:
            raise Http404()

        white_ip = ip_filter(access_ip)
        if white_ip:
            access_city = CompanyIp.objects.get(ip=white_ip).city
            access_legitimacy = True
        else:
            access_city = 'Non-company address'
            access_legitimacy = False

        lastest_access_list = Track.objects.filter(file_watermark=file_watermark).order_by('-access_time')

        if len(lastest_access_list) == 0:
            new_track_obj = Track.objects.create(file_watermark=file_watermark, access_ip=access_ip, access_time=access_time, access_UA=access_UA, access_city=access_city, access_legitimacy=access_legitimacy)
            redis.hmset(f'{file_watermark}[{access_time.strftime("%Y%m%d%H%M%S")}]', {'times':'1'})

            # 前端进行访问记录更新.向队列(左插)下发任务，因为时序关系,notify程序取任务进行ws通信时,必须右取.
            task_data = {'user_id': file_obj.file_sharer, 'file_watermark': file_watermark, 'access_ip':access_ip, 'access_time':timezone_to_string(access_time), 'access_UA':access_UA, 'access_city':access_city, 'access_legitimacy':access_legitimacy}
            redis.lpush('track_task', json.dumps(task_data))

            if file_obj.user_id != file_obj.file_sharer:
                task_data.update({'user_id':file_obj.user_id})
                redis.lpush('track_task', json.dumps(task_data))

        else:
            update_time = None
            TO_NOTIFY = None

            #if (access_time - lastest_access_list[0].access_time).total_seconds() < ACCESS_INTERVAL and redis.hget(f'{file_watermark}[{lastest_access_list[0].access_time.strftime("%Y%m%d%H%M%S")}]','times').decode('utf-8') != '2':

            # TODO:同一个打标记的文档,被不同ip同一时刻访问,需要进一步加入ip信息组成二元组进一步区分

            # 访问间隔默认值2s及以上，视为新的访问，进行该文件的访问记录再次记录
            if (access_time - lastest_access_list[0].access_time).total_seconds() >= ACCESS_INTERVAL:
                new_track_obj = Track.objects.create(file_watermark=file_watermark, access_ip=access_ip, access_time=access_time, access_UA=access_UA, access_city=access_city, access_legitimacy=access_legitimacy)
                redis.hmset(f'{file_watermark}[{access_time.strftime("%Y%m%d%H%M%S")}]', {'times':'1'})
                update_time = access_time
                TO_NOTIFY = True

                if not access_legitimacy:
                    # 向email_task队列下发邮件通知任务
                    email_data = {'user_id': file_obj.file_sharer, 'file_name': file_obj.file_name, 'file_owner':file_obj.user_id if file_obj.user_id!=file_obj.file_sharer else '',
                                  'upload_time': timezone_to_string(file_obj.upload_time),
                                  'access_time': timezone_to_string(access_time), 'access_ip': access_ip,
                                  'access_UA': access_UA}
                    redis.lpush('email_task', json.dumps(email_data))


            else:
                # 访问间隔默认值2s以内，且本次访问缓存还没有刷新2次，则更新访问记录、并刷新缓存
                if redis.hget(f'{file_watermark}[{lastest_access_list[0].access_time.strftime("%Y%m%d%H%M%S")}]','times').decode('utf-8') != '2':

                    lastest_access_list[0].access_UA = access_UA
                    lastest_access_list[0].save()
                    redis.hmset(f'{file_watermark}[{lastest_access_list[0].access_time.strftime("%Y%m%d%H%M%S")}]', {'times':'2'})
                    update_time = lastest_access_list[0].access_time
                    TO_NOTIFY = True

            if TO_NOTIFY:

                # 前端进行访问记录更新.向队列(左插)下发任务，因为时序关系,notify程序取任务进行ws通信时,必须右取.
                task_data = {'user_id': file_obj.file_sharer, 'file_watermark': file_watermark, 'access_ip': access_ip, 'access_time': timezone_to_string(update_time), 'access_UA': access_UA, 'access_UA':access_UA, 'access_city':access_city, 'access_legitimacy':access_legitimacy}
                redis.lpush('track_task', json.dumps(task_data))

                if file_obj.user_id != file_obj.file_sharer:
                    task_data.update({'user_id': file_obj.user_id})
                    redis.lpush('track_task', json.dumps(task_data))

        # win10打开doc,无论如何都只有一次访问记录.借助redis记录访问次数,当访问文档是doc时暂停2s再检测redis记录,如为达2则确定时win10打开doc场景,强制赋值并通知.
        # 判定access_UA是否为空的逻辑也可以整体修改为依靠redis的次数记录来判定
        # if file_obj.file_name.split('.')[-1] == 'doc':
        #     time.sleep(2)
        #     if redis.hget(f'{file_watermark}[{format_access_time}]','times') != '2':
        #         new_track_obj.access_UA = 'compatible; ms-office; MSOffice 16'
        #
        #         # 通知前端进行访问记录更新
        #         task_index = random.randint(0, QUEUE_MAX - 1)
        #         print('exec queue :', f'track_task{task_index}')
        #
        #         task_data = {'user_id': file_obj.file_sharer, 'file_watermark': file_watermark, 'access_ip': access_ip,
        #                      'access_time': format_access_time, 'access_UA': ''}
        #         redis.lpush(f'track_task{task_index}', json.dumps(task_data))
        #
        #         if file_obj.user_id != file_obj.file_sharer:
        #             task_data.update({'user_id': file_obj.user_id})
        #             redis.lpush(f'track_task{task_index}', json.dumps(task_data))

        raise Http404()#return HttpResponse('')
    else:
        raise Http404()