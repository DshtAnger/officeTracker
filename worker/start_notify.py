# coding:utf-8
import asyncio
import psutil
import os
import sys
import time
import logging
import json
from aredis import StrictRedis
import websockets
import traceback

programe_id = 15
psutil.Process().cpu_affinity([programe_id])

redis = StrictRedis(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'), password=os.getenv('REDIS_PASSWORD'))

hostServerName = os.getenv('hostServerName')

TRACK_QUEUE = 'track_task'

logging.basicConfig(format='%(message)s',filename = f'C:/Scribbles/notify.log', level=logging.INFO)
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.info("--------------------Uncaught Exception--------------------",exc_info=(exc_type, exc_value, exc_traceback))
sys.excepthook = handle_exception

def get_current_time():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

async def send_websocket_data(user_id, ws_data):
    try:
        async with websockets.connect(f'ws://{hostServerName}/ws/{user_id}/') as websocket:
            await websocket.send(json.dumps(ws_data))
    except Exception:
        exception_info = traceback.format_exc()
        logging.info(exception_info)

async def run():

    while 1:

        if not await redis.exists(TRACK_QUEUE):
            pass
        else:
            data = await redis.lpop(TRACK_QUEUE)
            data = json.loads(data.decode('utf-8'))

            user_id = data.get('user_id')
            file_watermark = data.get('file_watermark')
            access_ip = data.get('access_ip')
            access_time = data.get('access_time')
            access_UA = data.get('access_UA')

            await send_websocket_data(user_id, {'user_id':user_id, 'track_update': file_watermark, 'access_ip':access_ip, 'access_time':access_time, 'access_UA':access_UA})
            logging.info(f'[+][{get_current_time()}][{file_watermark}] Server had notified the front end to refresh the track status.')

            logging.info('-' * 50)

        await asyncio.sleep(0.3)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
print('[+] Start Nofity...')
loop.run_until_complete(run())