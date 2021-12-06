from django.db import models

# Create your models here.

class User(models.Model):
    user_id = models.CharField(max_length=32)
    user_passwd = models.CharField(max_length=64)
    user_ip = models.CharField(max_length=16)
    def __unicode__(self):
        return self.user_id

class File(models.Model):
    user_id = models.CharField(max_length=32)
    file_owner = models.CharField(max_length=32)
    file_name = models.CharField(max_length=128)
    file_size = models.CharField(max_length=9) #上传时要检测size不大于200M=209715200字节
    file_hash = models.CharField(max_length=32)

    file_data = models.CharField(max_length=32)

    upload_ip = models.CharField(max_length=32)
    upload_time = models.CharField(max_length=32)

    download_path = models.CharField(max_length=32)
    file_watermark = models.CharField(max_length=32)

    def __unicode__(self):
        return self.file_watermark

class Task(models.Model):
    user_id = models.CharField(max_length=32)
    file_watermark = models.CharField(max_length=32)
    task_time = models.CharField(max_length=32)
    taks_status = models.CharField(max_length=1)
    def __unicode__(self):
        return self.file_watermark

class Track(models.Model):
    user_id = models.CharField(max_length=32)
    file_watermark = models.CharField(max_length=32)
    access_ip = models.CharField(max_length=32)
    access_time = models.CharField(max_length=32)
    def __unicode__(self):
        return self.file_watermark