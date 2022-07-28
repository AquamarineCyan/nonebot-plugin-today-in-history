from datetime import date
import httpx
import json
import operator

import nonebot
from nonebot import on_command
from nonebot import require
from nonebot.plugin import PluginMetadata
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from nonebot.adapters.onebot.v11 import Message, MessageEvent
from nonebot_plugin_apscheduler import scheduler

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="历史上的今天",
    description="发送每日历史上的今天",
    usage="指令：历史上的今天",
    config=Config
)

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
        month = date.today().strftime("%m")
        day = date.today().strftime("%d")
        url1 = f"https://zhufred.gitee.io/zreader/ht/event/{month}{day}.json"
        url2 = f"https://zhufred.gitee.io/zreader/ht/ld/{month}{day}.json"
        r = await client.get(url1)
        r1 = await client.get(url2)
        content = json.loads(r.text)
        content1 = json.loads(r1.text)
        content += content1
        sort_data=sorted(content, key=operator.itemgetter('year'), reverse=False)   #排序
        today = f"{month}月{day}日"
        s = f"历史上的今天 {today}\n"
        for item in sort_data:
            s = s + f"{item['title']}\n"
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
