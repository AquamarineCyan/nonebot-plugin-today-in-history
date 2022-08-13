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


# api处理->json
def text_handle(text: str) -> json:
    # address = text.find("<\/a>")
    # print("<\/a> = ", address)
    # print(text[address:address + 5])
    text = text.replace("<\/a>", "")
    text = text.replace("\n", "")

    while True:
        address_head = text.find("<a target=")
        address_end = text.find(">", address_head)
        if address_head == -1 or address_end == -1:
            break
        # print("head = ", address_head)
        # print("end = ", address_end)
        text_middle = text[address_head:address_end + 1]
        # print(text_middle)
        text = text.replace(text_middle, "")

    # api返回的文本内容中含有双引号，无法直接转换json，故做临时处理，等待后续优化
    # 能跑就行.jpg
    month = date.today().strftime("%m")
    if month == "08":
        # 1
        address = text.find("Курск")
        text = text[:address - 1] + text[address + 6:]
        # 2
        address = text.find("第一次使用")
        text = text[:address - 3] + text[address + 13:]
        # 3
        address = text.find("克隆是英文")
        text = text[:address + 5] + text[address + 51:]

    data = json.loads(text)
    return data


# 信息获取
async def get_history_info() -> str:
    async with httpx.AsyncClient() as client:
        # content = json.loads(r.text)
        # url1 = f"https://zhufred.gitee.io/zreader/ht/event/{month}{day}.json"
        # url2 = f"https://zhufred.gitee.io/zreader/ht/ld/{month}{day}.json"
        # r = await client.get(url1)
        # r1 = await client.get(url2)
        # content = json.loads(r.text)
        # content1 = json.loads(r1.text)
        # content += content1
        # sort_data=sorted(content, key=operator.itemgetter('year'), reverse=False)   #排序
        month = date.today().strftime("%m")
        day = date.today().strftime("%d")
        url = f"https://baike.baidu.com/cms/home/eventsOnHistory/{month}.json"
        r = await client.get(url)
        if r.status_code == 200:
            print(r.encoding)
            r.encoding = "unicode_escape"
            print(r.encoding)
            print(len(r.text))
            data = text_handle(r.text)
            # today = f"{month}月{day}日"
            # s = f"历史上的今天 {today}\n"
            # for item in sort_data:
            #     s = s + f"{item['title']}\n"
            # print(s)
            # return s
            today = f"{month}{day}"
            s = f"历史上的今天 {today}\n"
            len_max = len(data[month][month + day])
            # print("len = ", len_max)
            for i in range(0, len_max):
                # print(data["08"]["0831"][i])
                # print(type(data["08"]["0831"][i]))
                str_year = data[month][today][i]["year"]
                str_title = data[month][today][i]["title"]
                if i == len_max - 1:
                    s = s + f"{str_year} {str_title}"  # 去除段末空行
                else:
                    s = s + f"{str_year} {str_title}\n"
            return s
        else:
            return "获取失败，请重试"


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
