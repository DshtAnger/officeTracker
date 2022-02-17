#coding:utf-8
import asyncio
import psutil
import os
import sys
import subprocess
import requests
import time
import logging
import json
from tornado.httpclient import AsyncHTTPClient
import websockets
import traceback

programe_id = int(sys.argv[1])#int(re.search('\d+',sys.argv[0]).group())
psutil.Process().cpu_affinity([programe_id])
print(f'programe_id: {programe_id}')

log_filename = f'watermake{programe_id}.log'
WATERMARK_QUEUE = f'watermark_task{programe_id}'
TRACK_QUEUE = f'track_task{programe_id}'

ERROR_LOG = ['does not have a recognized extension']

def get_current_time():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

from aredis import StrictRedis
redis = StrictRedis(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'), password=os.getenv('REDIS_PASSWORD'))

hostServerName = os.getenv('hostServerName')

logging.basicConfig(format='%(message)s',filename = f'C:/Scribbles/{log_filename}', level=logging.INFO)
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.info("--------------------Uncaught Exception--------------------",exc_info=(exc_type, exc_value, exc_traceback))
sys.excepthook = handle_exception

async def send_websocket_data(user_id, ws_data):
    try:
        async with websockets.connect(f'ws://{hostServerName}/ws/{user_id}/') as websocket:
            await websocket.send(json.dumps(ws_data))
    except Exception:
        exception_info = traceback.format_exc()
        logging.info(exception_info)

async def watermark(user_id, file_watermark, task_time, download_url):

    # task_status = False #( 0:Processing, 1:Finished, -1:Failed)

    file_name = download_url.split('/')[-1]

    file_path = f'C:/Scribbles/input/{file_watermark}'
    if not os.path.exists(file_path):
        os.mkdir(file_path)
    file_path = f'C:/Scribbles/input/{file_watermark}/{file_watermark}'
    if not os.path.exists(file_path):
        os.mkdir(file_path)

    #rsp = await AsyncHTTPClient().fetch(download_url)
    rsp = requests.get(download_url)
    # if rsp.status_code != 200:
    #     return
    with open( file_path + f'/{file_name}','wb' ) as f:
        f.write(rsp.content)
        #f.write(rsp.body)


    # 有些xls转换为xlsx文件后,想要再转换回xls后会出现弹框让你确认兼容性和轻微损失.修改后端C#代码不转换回xls,所以给实际文件名+x
    # ppt转为pptx后,想要再转回ppt时,源码1983:powerPointApp = new PowerPoint.Application()报错
    # [从 IClassFactory 为 CLSID 为 {91493441-5A91-11CF-8700-00AA0060263B} 的 COM 组件创建实例失败，原因是出现以下错误: 800706b5 接口未知。 (异常来自 HRESULT:0x800706B5)。]
    # 故ppt类型也不再从pptx转回ppt
    output_filename = file_name
    if output_filename.split('.')[-1] in ['xls', 'ppt']:
        output_filename = output_filename + 'x'

    # Scribbles_args = ['C:/Scribbles/Scribbles.exe',
    #                   '--urlScheme', 'http',
    #                   '--hostServerName', hostServerName,
    #                   '--hostRootPath', 'track',
    #                   '--hostSubDirs', '',
    #                   '--hostFileName', '',
    #                   '--hostFileExt', '',
    #                   '--identifierString', file_watermark,
    #                   '--inputDir', f'C:/Scribbles/input/{file_watermark}',
    #                   '--outputDir', 'C:/Scribbles/output',
    #                   ]
    # subprocess.check_output(Scribbles_args)

    Scribbles_args = ['C:/Scribbles/Scribbles.exe',
                      '--urlScheme=http',
                      f'--hostServerName={hostServerName}',
                      '--hostRootPath=track',
                      '--hostSubDirs=',
                      '--hostFileName=',
                      '--hostFileExt=',
                      f'--identifierString={file_watermark}',
                      f'--inputDir=C:/Scribbles/input/{file_watermark}',
                      '--outputDir=C:/Scribbles/output',
                      ]

    proc = await asyncio.create_subprocess_shell(' '.join(Scribbles_args),stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    logging.info(f'[+][{get_current_time()}][{file_watermark}] program stdout : {stdout} | program stderr : {stderr}')

    if b'does not have a recognized extension' in stdout:#.decode("unicode_escape") byte串中含中文,decode('utf-8')会报错，用这个编码
        task_status = False
        redis_result_data = {'task_status': task_status, 'task_time': task_time, 'failed_info': 'upload file does not have a recognized extension',
                             'file_watermark': file_watermark,
                             'download_url': ''}

    else:
        task_status = True
        redis_result_data = {'task_status': task_status, 'task_time': task_time, 'failed_info': '',
                             'file_watermark': file_watermark,
                             'download_url': f'http://11.139.50.114:8080/{file_watermark}/{output_filename}'}#172.18.18.28


    await redis.hmset(file_watermark, redis_result_data)
    logging.info(f'[+][{get_current_time()}][{file_watermark}] Done task and return redis Hash data: {redis_result_data}')

    try:
        rsp = await AsyncHTTPClient().fetch(f'http://{hostServerName}/notify/task/{file_watermark}')
        logging.info(f'[+][{get_current_time()}][{file_watermark}] Server {rsp.body.decode("utf-8")}')
    except:
        pass

    await send_websocket_data(user_id, {'user_id':user_id, 'download_update':file_watermark, 'is_success': task_status})
    logging.info(f'[+][{get_current_time()}][{file_watermark}] Server had notified the front end to refresh the download status.')

async def run():

    while 1:

        if not await redis.exists(WATERMARK_QUEUE):
            pass
            #logging.info(f'[*][{get_current_time()}] {WATERMARK_QUEUE} is empty.')
            #await asyncio.sleep(1)
            #continue
        else:
            data = await redis.lpop(WATERMARK_QUEUE)
            data = json.loads(data.decode('utf-8'))

            user_id = data.get('user_id')
            file_watermark = data.get('file_watermark')
            task_time = data.get('task_time')
            download_url = data.get('download_url')

            logging.info(f'[+][{get_current_time()}][{file_watermark}] Get task : {data}')

            await watermark(user_id, file_watermark, task_time, download_url)

            logging.info('-'*50)

        await asyncio.sleep(0.2)

# loop = asyncio.get_event_loop()
# loop.run_until_complete(asyncio.gather(asyncio.ensure_future(run())))

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(run())