from django.db import models
from django.forms import ModelForm

# Create your models here.

from django.conf import settings
import os

# if settings.DEBUG:
#     uplaod_to = f'./upload/'
# else:
#     uplaod_to = f'./{os.path.join(settings.BASE_DIR, "upload")}'

class User(models.Model):
    user_id = models.CharField(max_length=32)
    user_passwd = models.CharField(max_length=64)
    user_ip = models.CharField(max_length=16)
    def __unicode__(self):
        return self.user_id

class File(models.Model):
    # linux中文件名最长为255字符，文件路径最大长度为4096字符
    user_id = models.CharField(max_length=32)#表示该文件的上传归属人
    file_sharer = models.CharField(max_length=32)
    file_name = models.CharField(max_length=255)
    file_size = models.CharField(max_length=9) #上传时要检测size不大于200M=209715200字节
    file_hash = models.CharField(max_length=64)

    upload_file_path = models.CharField(max_length=4096)#models.FileField(upload_to=uplaod_to)

    upload_ip = models.CharField(max_length=32)
    upload_time = models.DateTimeField()

    download_file_path = models.CharField(max_length=4096)
    file_watermark = models.CharField(max_length=64)

    def __unicode__(self):
        return self.file_watermark

class Task(models.Model):
    file_watermark = models.CharField(max_length=64)
    task_time = models.DateTimeField()
    taks_status = models.CharField(max_length=1)
    def __unicode__(self):
        return self.file_watermark

class Track(models.Model):
    file_watermark = models.CharField(max_length=64)
    access_ip = models.CharField(max_length=32)
    access_time = models.DateTimeField()
    access_UA = models.CharField(max_length=1024)
    def __unicode__(self):
        return self.file_watermark

class CompanyIp(models.Model):
    ip = models.CharField(max_length=32)
    type = models.CharField(max_length=32)
    city = models.CharField(max_length=32)
    region = models.CharField(max_length=32)
    campus = models.CharField(max_length=32)
    update_time = models.DateTimeField()
    def __unicode__(self):
        return self.ip
