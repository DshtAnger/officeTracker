import asyncio
import threading
import os
import sys
import subprocess
import time
import datetime
import logging
import json
from tornado.httpclient import AsyncHTTPClient
from tornado.platform.asyncio import AsyncIOMainLoop

def get_current_time():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

from aredis import StrictRedis
redis = StrictRedis(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'), password=os.getenv('REDIS_PASSWORD'))

hostServerName = os.getenv('hostServerName')

logging.basicConfig(format='%(message)s',filename = 'C:/Scribbles/watermake.log', level=logging.INFO)
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.info("--------------------Uncaught Exception--------------------",exc_info=(exc_type, exc_value, exc_traceback))
sys.excepthook = handle_exception


sem = asyncio.Semaphore(100)

class TaskStat:
    instance = None
    tasks = {}   # 使用redis/rabbitmq
    # lock = asyncio.Semaphore(value=1)   # 线程锁，防止同时修改
    task_id = 0

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            cls.instance = object.__new__(cls, *args, **kwargs)
        return cls.instance

    def __init__(self):
        pass

    @classmethod
    def add_task(cls, task_name, user='USER', task_type='loop', context=None):
        '''
        添加任务, 线程不安全

        :param task_name: 任务名称
        :param user: 调用用户, 默认为USER主线程
        :param task_type: 任务类型: loop/timer
        '''

        # await cls.lock.acquire()
        logging.info(f'ADD TASK: {task_name} {user} {task_type}')
        cls.task_id += 1
        task = {
            'task_id': cls.task_id,
            'task_name': task_name,
            'user': user,
            'task_type': task_type,
            'context': context,
            'status': 'created',
            'create_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'update_time': None,
        }
        cls.tasks.update({cls.task_id: task})
        task_id = cls.task_id
        # await cls.lock.release()
        return task_id

    @classmethod
    def get_task(cls, user=None, task_name=None):
        ans = {}
        if user is None:    # 用户未指定，给出所有结果
            ans = cls.tasks
        else:   # 用户指定，筛选
            for k, v in cls.tasks:
                if v.get('user') == user and (task_name is None or v.get('task_name') == task_name):
                    ans[k] = v
        return ans

    @classmethod
    def change_task_status(cls, task_id, status):
        if task_id not in cls.tasks:
            logging.error(f'{task_id} is not found')
            return 100002
        else:
            # await cls.lock.acquire()
            cls.tasks[task_id]['status'] = status
            cls.tasks[task_id]['update_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # await cls.lock.release()
            logging.info(f'{task_id} status => {status}')
            return 100001


def new_loop(loop, future, sem):
    asyncio.set_event_loop(loop)
    # loop.run_forever()
    loop.run_until_complete(future)
    sem.release()


def new_thread_task(func, sem, *args, **kwargs):
    logging.info(f'run {func} {args} {kwargs}')
    asyncio.run(func(*args, **kwargs))
    sem.release()


async def create_thread_task(task, *args, **kwargs):
    '''
    在新loop线程内执行, 存放servers等监听程序, 不会调用回调来修改任务状态

    :param task: coro
    '''
    context = None
    await sem.acquire()
    loop = asyncio.new_event_loop()
    t = threading.Thread(target=new_thread_task, args=(task, sem, *args))
    # t = threading.Thread(target=new_loop, args=(loop, task(*args, **kwargs), sem))
    t.start()
    context = asyncio.run_coroutine_threadsafe(task(*args, **kwargs), loop)
    return context


def add_async_task(task, create_new=False, *args, **kwargs):
    '''
    执行新任务, 存放servers等监听程序, 不会调用回调来修改任务状态

    :param task: coro
    '''
    context = None
    if create_new:
        loop = asyncio.get_event_loop()
        context = asyncio.run_coroutine_threadsafe(create_thread_task(task, *args, **kwargs), loop)
    else:
        loop = asyncio.get_event_loop()
        context = asyncio.run_coroutine_threadsafe(task(*args, **kwargs), loop)
    try:
        task_module = task.__module__
    except:
        task_module = ''
    try:
        task_name = task.__name__
    except:
        task_name = ''
    name = f'{task_module}.{task_name}'
    # stat = asyncio.run_coroutine_threadsafe(TaskStat().add_task(name, context=context), loop)
    stat = TaskStat().add_task(name, context=context)
    return stat, context


def get_async_task(loop=None):
    return asyncio.current_task(loop)


def get_async_not_done(loop=None):
    return asyncio.all_tasks(loop)


def convert_coroutine(callable, *args, **kwargs):
    """
    coroutine/callable => coroutine
    """
    if asyncio.iscoroutine(callable):
        return callable

    return asyncio.coroutine(callable)(*args, **kwargs)


def fire(callable, *args, **kwargs):
    '''
    coroutine => future
    '''
    return asyncio.ensure_future(convert_coroutine(callable, *args, **kwargs))


async def _call_later(delay, callable, *args, **kwargs):
    '''
    sync
    '''
    await asyncio.sleep(delay)
    fire(callable, *args, **kwargs)


def add_async_task_delay(delay, task, *args, **kwargs):
    '''
    设定程序延迟一定时间后运行

    :param delay: int seconds
    :parms task: function,
    '''
    try:
        task_module = task.__module__
    except:
        task_module = ''
    try:
        task_name = task.__name__
    except:
        task_name = ''
    name = f'delay task {task_module}.{task_name}'

    context = fire(_call_later, delay, task, *args, **kwargs)
    stat = TaskStat().add_task(name, context)
    return stat, context


# result = subprocess.call(args)

# result_srting = result.decode('utf-8')

# print(result_srting)

async def run():

    while 1:

        QUEUE = 'watermark_task'

        if not await redis.exists(QUEUE):
            logging.info(f'[*][{get_current_time()}] {QUEUE} is empty.')
            await asyncio.sleep(1)
            continue

        data = await redis.lpop(QUEUE)
        data = json.loads(data.decode('utf-8'))

        task_id = data.get('task_id')
        task_time = data.get('task_time')
        download_url = data.get('download_url')
        file_watermark = data.get('file_watermark')

        logging.info(f'[+][{get_current_time()}][{task_id}] Get task : {data}')


        await watermark(task_id,task_time,file_watermark,download_url)

        #add_async_task(watermark,False,[task_id,task_time,file_watermark,download_url])

        #await asyncio.sleep(3)


async def watermark(task_id,task_time,file_watermark,download_url):

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

    redis_result_data = {'task_status': '1', 'task_time': task_time, 'failed_info': '', 'file_watermark': file_watermark, 'download_url': f'http://172.18.18.28:8080/{file_watermark}/{file_name}'}
    await redis.hmset(task_id, redis_result_data)

    logging.info(f'[+][{get_current_time()}][{task_id}] Done task : {redis_result_data}')


loop = asyncio.get_event_loop()
loop.run_until_complete(asyncio.gather(asyncio.ensure_future(run())))

