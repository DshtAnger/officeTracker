import asyncio
import os
import sys
import subprocess
import random
import logging
from tornado import httpclient
from io import BytesIO


class Async(object):

    instance = None

    workers = 10

    sem = asyncio.Semaphore(workers)

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            cls.instance = object.__new__(cls, *args, **kwargs)
        return cls.instance

    def __init__(self):
        httpclient.AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient", defaults=dict(connect_timeout=3600, request_timeout=3600))
        self.client = httpclient.AsyncHTTPClient()

    @classmethod
    def get_request(cls, *args, **kwargs):
        return httpclient.HTTPRequest(*args, **kwargs)

    @classmethod
    async def fetch(cls, request):
        async with cls.instance.sem:
            response = await cls().client.fetch(request, False)
            return response

    @classmethod
    async def get(cls, url, headers={}, body=None, connect_timeout=None, request_timeout=None, follow_redirects=True, proxy_host=None, proxy_port=None, validate_cert=False):
        request = cls().get_request(url=url, method='GET', headers=headers, body=body, connect_timeout=connect_timeout,
                                    request_timeout=request_timeout, follow_redirects=follow_redirects, proxy_host=proxy_host, proxy_port=proxy_port, validate_cert=False)
        resp = await cls().fetch(request)
        return resp

    @classmethod
    async def post(cls, url, headers={}, body=None, connect_timeout=None, request_timeout=None, follow_redirects=True, proxy_host=None, proxy_port=None, validate_cert=False):
        request = cls().get_request(url=url, method='POST', headers=headers, body=body, connect_timeout=connect_timeout,
                                    request_timeout=request_timeout, follow_redirects=follow_redirects, proxy_host=proxy_host, proxy_port=proxy_port, validate_cert=False)
        resp = await cls().fetch(request)
        return resp


from aredis import StrictRedis
redis = StrictRedis(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'), password=os.getenv('REDIS_PASSWORD'))

log_dir = '/root'
if not os.path.exists(log_dir):
    os.mkdir(log_dir)
logging.basicConfig(format='%(message)s',filename = log_dir + '/watermake.log', level=logging.INFO)
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.info("--------------------Uncaught Exception--------------------",exc_info=(exc_type, exc_value, exc_traceback))
sys.excepthook = handle_exception

# args = [r'C:\Users\Administrator\Desktop\Scribbles\Scribbles\bin\Release\Scribbles.exe',
# '--urlScheme','http',
# '--hostServerName','119.91.94.25',
# '--hostRootPath','',
# '--hostSubDirs','',
# '--hostFileName','light-icon',
# '--hostFileExt','.gif',
# '--identifierString','hjk523rdscxa6',
# '--inputDir',r'C:\Users\Administrator\Desktop\Scribbles\Scribbles\bin\Release\InputDir',
# '--outputDir',r'C:\Users\Administrator\Desktop\Scribbles\Scribbles\bin\Release\OutputDir',
# ]

# result = subprocess.call(args)

# result_srting = result.decode('utf-8')

# print(result_srting)

async def run():

    while 1:

        QUEUE = 'watermark_task_queue'

        if not await redis.exists(QUEUE):
            logging.info(f'{QUEUE} is empty.')
            await asyncio.sleep(3)
            continue

        data = await redis.lpop(QUEUE)

        logging.info(f'Get task data from {QUEUE}: {data}')

        # await do_work(do_scan,data,timeout=2 * 3600,delta_time=1,NAME=NAME)

        url = data.decode('utf-8')

        await watermark(url,str(random.randint(1,999999)))

        await asyncio.sleep(3)

        return 'ok'

async def watermark(url='',watermark_string=''):
    rsp = await Async.get(url)
    with open(watermark_string+'.html','wb') as f:
        f.write(rsp.body)
    logging.info(url+' ok.')


loop = asyncio.get_event_loop()

tasks = []
task = asyncio.ensure_future(run())
tasks.append(task)

res = loop.run_until_complete(asyncio.gather(*tasks))


#context = asyncio.run_coroutine_threadsafe(run, loop)