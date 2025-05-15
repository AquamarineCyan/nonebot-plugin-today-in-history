import asyncio
from datetime import date, datetime
from pathlib import Path

import httpx
from nonebot import require
from nonebot.adapters.onebot.v11 import Bot
from nonebot.log import logger

try:
    import ujson as json
except ModuleNotFoundError:
    import json

require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store

PUSHDATA_FILE: Path = Path(__file__).parent / "PUSHDATA.json"


def read_json(file: Path = PUSHDATA_FILE) -> dict:
    if file.exists():
        with open(file, encoding="utf-8") as f:
            data = json.load(f)
        return data
    else:
        return {}


def write_json(data: dict, file: Path = PUSHDATA_FILE) -> None:
    with file.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def _html_to_json_handle(text: str) -> json:
    """去除api返回内容中不符合json格式的部分"""
    text = text.replace("<\/a>", "")
    text = text.replace("\n", "")

    # 去除html标签
    while True:
        address_head = text.find("<a target=")
        address_end = text.find(">", address_head)
        if address_head == -1 or address_end == -1:
            break
        text_middle = text[address_head : address_end + 1]
        text = text.replace(text_middle, "")

    # 去除key:desc值
    address_head: int = 0
    while True:
        address_head = text.find('"desc":', address_head)
        address_end = text.find('"cover":', address_head)
        if address_head == -1 or address_end == -1:
            break
        text_middle = text[address_head + 8 : address_end - 2]
        address_head = address_end
        text = text.replace(text_middle, "")

    # 去除key:title中多引号
    address_head: int = 0
    while True:
        address_head = text.find('"title":', address_head)
        address_end = text.find('"festival"', address_head)
        if address_head == -1 or address_end == -1:
            break
        text_middle = text[address_head + 9 : address_end - 2]
        if '"' in text_middle:
            text_middle = text_middle.replace('"', " ")
            text = text[: address_head + 9] + text_middle + text[address_end - 2 :]
        address_head = address_end

    return json.loads(text)


async def get_history_info(retry: int = 3) -> str:
    """获取历史上的今天信息"""
    for _ in range(retry):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                month = date.today().strftime("%m")
                day = date.today().strftime("%d")
                url = f"https://baike.baidu.com/cms/home/eventsOnHistory/{month}.json"

                r = await client.get(url)
                r.raise_for_status()  # 自动处理HTTP错误
                r.encoding = "unicode_escape"

                data = _html_to_json_handle(r.text)
                today = f"{month}{day}"
                info = f"历史上的今天 {today}\n"
                len_max = len(data[month][month + day])

                for i in range(0, len_max):
                    str_year = data[month][today][i]["year"]
                    str_title = data[month][today][i]["title"]
                    if i == len_max - 1:
                        info = info + f"{str_year} {str_title}"  # 去除段末空行
                    else:
                        info = info + f"{str_year} {str_title}\n"

                return info

        except (httpx.RequestError, json.JSONDecodeError) as e:
            logger.error(f"获取历史信息失败: {e}")
            await asyncio.sleep(2)


async def refresh_group_list(bot: Bot) -> list:
    """获取群聊列表"""
    groups = await bot.call_api("get_group_list", no_cache=True)
    g_list = []
    for group in groups:
        g_list.append(group["group_id"])
    return g_list


async def get_history_info_with_cache() -> str:
    """获取历史上的今天信息，同步更新缓存"""
    today = int(datetime.now().strftime("%Y%m%d"))
    cache_file = store.get_plugin_cache_file("history_cache.json")

    if cache_file.exists():
        read_data = read_json(cache_file)
        if read_data.get("date") == today:
            logger.info("今天数据已存在，跳过更新")
            return read_data.get("info")

    info = await get_history_info()
    if info:
        data_dict = {"date": today, "info": info}
        with cache_file.open("w", encoding="utf-8") as f:
            json.dump(data_dict, f, ensure_ascii=False, indent=4)
    return info
