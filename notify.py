# coding:utf-8
import asyncio
import psutil
import os
import sys
import time
import logging
import json
from aredis import StrictRedis
from aiohttp import ClientSession
import hashlib
import random
import websockets
import traceback

programe_id = 15
psutil.Process().cpu_affinity([programe_id])

redis = StrictRedis(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'), password=os.getenv('REDIS_PASSWORD'))

HOST_SERVER = os.getenv('HOST_SERVER')

TRACK_QUEUE = 'track_task'

NOTIFY_QUEUE = 'notify_task'

EMAIL_QUEUE = 'email_task'

# 办公机上访问OA区、IDC皆可,云梯申请到的机器位于IDC生产环境、只能访问IDC区
paasId = os.getenv('paasId')
paasToken = os.getenv('paasToken')
server = "http://idc.rio.tencent.com"
path = "/ebus/tof4_msg/api/v1/Message/SendMailInfo"

logging.basicConfig(format='%(message)s', filename=f'/root/officeTracker/notify.log', level=logging.INFO)
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.info("--------------------Uncaught Exception--------------------",
                 exc_info=(exc_type, exc_value, exc_traceback))
sys.excepthook = handle_exception


def get_current_time():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


async def send_websocket_data(user_id, ws_data):
    try:
        async with websockets.connect(f'ws://127.0.0.1:8888/ws/{user_id}/') as websocket:
            await websocket.send(json.dumps(ws_data))
    except Exception:
        exception_info = traceback.format_exc()
        logging.info(exception_info)

def gen_header():
    timestamp = str(int(time.time()))
    nonce = str(random.randint(1000, 9999))
    signature = hashlib.sha256((timestamp + paasToken + nonce + timestamp).encode()).hexdigest().upper()

    header = {}
    header['x-rio-paasid'] = paasId
    header['x-rio-nonce'] = nonce
    header['x-rio-timestamp'] = timestamp
    header['x-rio-signature'] = signature

    return header


async def send_email(user_id, upload_time, file_name, file_owner, access_time, access_ip, access_UA):
    try:

        data = {
            "From": "YD-OfficeTracker@tencent.com",
            "To": "%s@tencent.com" % user_id,
            "CC": file_owner,
            "Bcc": "",
            "Title": "【警告】您的文档已被非法访问",

            "Content": '''
			<h2>Dear %s:</h2>
			<h3>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;您于%s在平台上传的文档"%s"已被公司外的非法地址访问，具体非法访问信息如下:</h3>
			<h3>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;访问时间:%s</h3>
			<h3>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;访问地址:%s</h3>
			<h3>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;访问指纹:"%s"</h3>
			''' % (user_id, upload_time, file_name, access_time, access_ip, access_UA),

            "EmailType": 1,  # MAIL_TX = 1,     MAIL_INTERNET = 0. 收件人包含内外部的，需要将EmailType设置为0
            "BodyFormat": 1,  # HTML_FORMAT = 1, TEXT_FORMAT = 0
            "Priority": 0
        }

        async with ClientSession() as session:
            async with session.post(server + path, headers=gen_header(), data=json.dumps(data)) as response:
                if response.status == 200:
                    logging.info(f'[+][{get_current_time()}][{user_id}] {file_name} was accessed illegally at {access_time} by {access_ip} with UA:{access_UA}.')
                else:
                    logging.info(f'[*][{get_current_time()}][{user_id}] send email error with text: {response.text}')
    except Exception:
        exception_info = traceback.format_exc()
        logging.info(exception_info)




async def run():
    while 1:

        if not await redis.exists(TRACK_QUEUE):
            pass
        else:
            # 必须右取任务
            data = await redis.rpop(TRACK_QUEUE)
            data = json.loads(data.decode('utf-8'))

            user_id = data.get('user_id')
            file_watermark = data.get('file_watermark')
            access_ip = data.get('access_ip')
            access_time = data.get('access_time')
            access_UA = data.get('access_UA')
            access_city = data.get('access_city')
            access_legitimacy = data.get('access_legitimacy')

            await send_websocket_data(user_id,
                                      {'user_id': user_id, 'track_update': file_watermark, 'access_ip': access_ip,
                                       'access_time': access_time, 'access_UA': access_UA, 'access_city': access_city,
                                       'access_legitimacy': access_legitimacy})
            logging.info(
                f'[+][{get_current_time()}][{file_watermark}] Server had notified the front end to refresh the track status.')

            logging.info('-' * 50)

        if not await redis.exists(NOTIFY_QUEUE):
            pass
        else:
            data = await redis.rpop(NOTIFY_QUEUE)
            data = json.loads(data.decode('utf-8'))

            user_id = data.get('user_id')
            file_watermark = data.get('download_update')

            await send_websocket_data(user_id, data)
            logging.info(
                f'[+][{get_current_time()}][{file_watermark}] Server had notified the front end to refresh the download status.')

            logging.info('-' * 50)

        if not await redis.exists(EMAIL_QUEUE):
            pass
        else:
            data = await redis.rpop(EMAIL_QUEUE)
            data = json.loads(data.decode('utf-8'))

            user_id = data.get('user_id')
            upload_time = data.get('upload_time')
            file_name = data.get('file_name')
            file_owner = data.get('file_owner')
            access_time = data.get('access_time')
            access_ip = data.get('access_ip')
            access_UA = data.get('access_UA')

            logging.info(f'[+][{get_current_time()}][{user_id}] Get task data: {data}')
            await send_email(user_id, upload_time, file_name, file_owner, access_time, access_ip, access_UA)

            logging.info('-' * 50)

        await asyncio.sleep(0.3)


loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
print('[+] Start Nofity...')
loop.run_until_complete(run())
