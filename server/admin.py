from django.contrib import admin

# Register your models here.

from server.models import *

class UserAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'user_passwd', 'user_ip')
    search_fields = ('user_id', 'user_ip')

class FileAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'file_name', 'file_hash', 'upload_ip', 'upload_time', 'file_watermark')
    search_fields = ('user_id', 'file_name', 'file_hash', 'upload_ip', 'upload_time', 'file_watermark')
    list_filter = ('user_id', 'upload_time', 'upload_ip')

class TaskAdmin(admin.ModelAdmin):
    list_display = ('file_watermark', 'task_time', 'taks_status')
    search_fields = ('file_watermark', 'task_time', 'taks_status',)
    list_filter = ('file_watermark', 'task_time', 'taks_status')

class TrackAdmin(admin.ModelAdmin):
    list_display = ('file_watermark', 'access_ip', 'access_time')
    search_fields = ('file_watermark', 'access_ip', 'access_time')
    list_filter = ('file_watermark', 'access_ip', 'access_time')

admin.site.register(User,UserAdmin)
admin.site.register(File,FileAdmin)
admin.site.register(Task,TaskAdmin)
admin.site.register(Track,TrackAdmin)