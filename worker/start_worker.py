# coding=utf-8
import sys
import asyncio
import logging
import traceback

# https://blog.csdn.net/HighDS/article/details/103867368

QUEUE_MAX = 10

logging.basicConfig(format='%(message)s',filename = f'C:/Scribbles/run.log', level=logging.INFO)
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.info("--------------------Uncaught Exception--------------------",exc_info=(exc_type, exc_value, exc_traceback))
sys.excepthook = handle_exception

async def start_do_watermark(programe_id):
    try:
        await asyncio.create_subprocess_shell(f'python C:/Scribbles/do_watermark.py {programe_id}', stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
    except:
        exception_info = traceback.format_exc()
        logging.info(f'programe_id: {programe_id}\n' + exception_info + '\n' + '-'*100)
        raise

loop = asyncio.get_event_loop()

tasks = []

for programe_id in range(0,QUEUE_MAX):
    task = asyncio.ensure_future( start_do_watermark(programe_id) )
    tasks.append(task)

print('[+] Start Worker...')

loop.run_until_complete(asyncio.gather(*tasks))