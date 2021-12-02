import asyncio
import psutil
import os
import sys
import subprocess
import time
import logging
import json
from tornado.httpclient import AsyncHTTPClient

#re.search('\d+','do_watermakr1.py').group()
programe_id = 1#int(sys.argv[0].split('.')[0][-1])

psutil.Process().cpu_affinity([programe_id])


log_filename = f'watermake{programe_id}.log'
QUEUE = f'watermark_task{programe_id}'

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

async def watermark(file_watermark,task_time,download_url):

    file_name = download_url.split('/')[-1]

    file_path = f'C:/Scribbles/input/{file_watermark}'
    if not os.path.exists(file_path):
        os.mkdir(file_path)
    file_path = f'C:/Scribbles/input/{file_watermark}/{file_watermark}'
    if not os.path.exists(file_path):
        os.mkdir(file_path)

    rsp = await AsyncHTTPClient().fetch(download_url)
    #rsp = requests.get(download_url)
    with open( file_path + f'/{file_name}','wb' ) as f:
        f.write(rsp.body)

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
    logging.info(f'[+][{get_current_time()}][{file_watermark}] program stdout : {stdout}')

    redis_result_data = {'task_status': '1', 'task_time': task_time, 'failed_info': '', 'file_watermark': file_watermark, 'download_url': f'http://172.18.18.28:8080/{file_watermark}/{file_name}'}
    await redis.hmset(file_watermark, redis_result_data)
    logging.info(f'[+][{get_current_time()}][{file_watermark}] Done task : {redis_result_data}')

    try:
        rsp = await AsyncHTTPClient().fetch(f'http://{hostServerName}/notify/task/{file_watermark}')
        logging.info(f'[+][{get_current_time()}][{file_watermark}] Server {rsp.body}')
    except:
        pass


async def run():

    while 1:

        if not await redis.exists(QUEUE):
            logging.info(f'[*][{get_current_time()}] {QUEUE} is empty.')
            await asyncio.sleep(1)
            continue

        data = await redis.lpop(QUEUE)
        data = json.loads(data.decode('utf-8'))

        task_time = data.get('task_time')
        download_url = data.get('download_url')
        file_watermark = data.get('file_watermark')

        logging.info(f'[+][{get_current_time()}][{task_id}] Get task : {data}')

        await watermark(file_watermark,task_time,download_url)

        #add_async_task(watermark,False,[task_id,task_time,file_watermark,download_url])

        #await asyncio.sleep(3)




# loop = asyncio.get_event_loop()
# loop.run_until_complete(asyncio.gather(asyncio.ensure_future(run())))

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(run())