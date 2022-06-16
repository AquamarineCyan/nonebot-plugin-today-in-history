from datetime import date
import requests
import json

from nonebot import on_regex
from .config import Config
from nonebot import require
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import json
import nonebot
from nonebot.adapters.onebot.v11 import Message


global_config = nonebot.get_driver().config
# nonebot.logger.info("global_config:{}".format(global_config))
plugin_config = Config(**global_config.dict())
# nonebot.logger.info("plugin_config:{}".format(plugin_config))
scheduler = require("nonebot_plugin_apscheduler").scheduler  # type:AsyncIOScheduler

def remove_upprintable_chars(s):
    return ''.join(x for x in s if x.isprintable())  # 去除imageUrl可能存在的不可见字符

#history = on_regex('历史上的今天', priority=15) # 后续开发


async def today_in_histoty():
    #global msg  # msg改成全局，方便在另一个函数中使用
    msg = await history()
    for qq in plugin_config.history_qq_friends:
        await nonebot.get_bot().send_private_msg(user_id=qq, message=Message(msg))

    for qq_group in plugin_config.history_qq_groups:
        await nonebot.get_bot().send_group_msg(group_id=qq_group, message=Message(msg)) # MessageEvent可以使用CQ发图片


async def history():
    try:
        url = "https://api.iyk0.com/lishi/"
        r = requests.get(url)
        content = json.loads(r.text)
        month = date.today().strftime('%m')
        day = date.today().strftime('%d')
        today = f'{month}月{day}日'
        i = 0
        s = '历史上的今天' + ' ' + today + '\n'
        for item in content[today]:
            s = s + item['year'] + ' ' + item['title'] + '\n'
        print(s)
        return s
    except:
        pass

for index, time in enumerate(plugin_config.history_inform_time):
    nonebot.logger.info("id:{},time:{}".format(index, time))
    scheduler.add_job(today_in_histoty, 'cron', hour=time['HOUR'], minute=time['MINUTE'])