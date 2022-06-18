from datetime import date
import httpx
import json

import nonebot
from nonebot import on_command
from .config import Config
from nonebot import require
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from nonebot.adapters.onebot.v11 import Message, MessageEvent
from nonebot_plugin_apscheduler import scheduler

global_config = nonebot.get_driver().config
plugin_config = Config(**global_config.dict())

history_matcher = on_command('历史上的今天', priority=15)


@history_matcher.handle()
async def _(event: MessageEvent):
    mes = await get_history_info()
    await history_matcher.finish(mes)


# 信息获取
async def get_history_info() -> str:
    async with httpx.AsyncClient() as client:
        url = "https://api.iyk0.com/lishi/"
        r = await client.get(url)
        content = json.loads(r.text)
        month = date.today().strftime("%m")
        day = date.today().strftime("%d")
        today = f"{month}月{day}日"
        s = f"历史上的今天 {today}\n"
        for item in content[today]:
            s = s + f"{item['year']} {item['title']}\n"
        print(s)
        return s


# 消息发送
async def send_mes_today_in_histoty():
    # global msg  # msg改成全局，方便在另一个函数中使用
    msg = await get_history_info()
    for qq in plugin_config.history_qq_friends:
        await nonebot.get_bot().send_private_msg(user_id=qq, message=Message(msg))

    for qq_group in plugin_config.history_qq_groups:
        await nonebot.get_bot().send_group_msg(group_id=qq_group, message=Message(msg))  # MessageEvent可以使用CQ发图片


# 定时任务
for index, time in enumerate(plugin_config.history_inform_time):
    nonebot.logger.info("id:{},time:{}".format(index, time))
    scheduler.add_job(send_mes_today_in_histoty, 'cron', hour=time.hour, minute=time.minute)
