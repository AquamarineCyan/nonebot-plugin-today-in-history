import re

from nonebot import get_bot, get_driver, logger, on_command, require
from nonebot.adapters.onebot.v11 import Message, GroupMessageEvent, MessageEvent, MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import Arg, CommandArg
from nonebot.typing import T_State

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

from .config import PUSHDATA_ENV
from .utils import *

driver = get_driver()


@driver.on_startup
async def subscribe_jobs():
    PUSHDATA = read_json()
    PUSHDATA_ENV.update(PUSHDATA)
    write_json(PUSHDATA_ENV)
    PUSHDATA_ENV_FILE = Path(__file__).parent / "PUSHDATA_ENV.json"
    with PUSHDATA_ENV_FILE.open("w", encoding="utf-8") as f:
        json.dump(PUSHDATA_ENV, f, ensure_ascii=False, indent=4)

    for id, value in PUSHDATA_ENV.items():
        scheduler.add_job(
            push_send,
            "cron",
            args=[id],
            id=f"history_push_{id}",
            replace_existing=True,
            hour=value["hour"],
            minute=value["minute"],
        )
        logger.info(f"{id},{value['hour']}:{value['minute']}")


async def push_send(id: str):
    bot = get_bot()
    if id[0:2] == "g_":
        msg = await get_history_info("pic")
        await bot.call_api("send_group_msg", group_id=int(id[2:]), message=msg)
    else:
        msg = await get_history_info("text")
        await bot.call_api("send_private_msg", user_id=id[2:], message=msg)


def calendar_subscribe(id: str, hour: int, minute: int) -> None:
    PUSHDATA_NEW = {}
    PUSHDATA_NEW.setdefault(
        id,
        {
            "hour": hour,
            "minute": minute
        }
    )
    PUSHDATA = read_json()
    PUSHDATA.update(PUSHDATA_NEW)
    write_json(PUSHDATA)

    scheduler.add_job(
        push_send,
        "cron",
        args=[id],
        id=f"history_push_{id}",
        replace_existing=True,
        hour=hour,
        minute=minute,
    )
    logger.info(f"[{id}]设置历史上的今天推送时间为：{hour}:{minute}")


push_matcher = on_command("历史上的今天")


@push_matcher.handle()
async def _(
    event: MessageEvent,
    matcher: Matcher,
    args: Message = CommandArg()
):
    if isinstance(event, GroupMessageEvent):
        id = "g_{}".format(event.group_id)
    else:
        id = "f_{}".format(event.user_id)
    if cmdarg := args.extract_plain_text():
        if "状态" in cmdarg:
            push_state = scheduler.get_job(f"history_push_{id}")
            if push_state:
                PUSHDATA = read_json()
                push_data = PUSHDATA.get(id)
                msg = (
                    f"推送时间: {push_data['hour']}:{push_data['minute']}"
                )
                await matcher.finish(msg)
        elif "设置" in cmdarg or "推送" in cmdarg:
            if ":" in cmdarg or "：" in cmdarg:
                matcher.set_arg("time_arg", args)
        elif "取消" in cmdarg or "关闭" in cmdarg:
            PUSHDATA = read_json()
            PUSHDATA.pop(id)
            write_json(PUSHDATA)
            scheduler.remove_job(f"history_push_{id}")
            logger.info(f"[{id}] remove")
            await matcher.finish("历史上的今天推送已禁用")
        else:
            await matcher.finish("历史上的今天的推送参数不正确")
    else:
        msg = await get_history_info("image")
        await matcher.finish(msg)


@push_matcher.got("time_arg", prompt="请发送每日定时推送日历的时间，格式为：小时:分钟")
async def handle_time(
    event: MessageEvent,
    matcher: Matcher,
    state: T_State,
    time_arg: Message = Arg()
):
    state.setdefault("max_times", 0)
    time = time_arg.extract_plain_text()
    if any(cancel in time for cancel in ["取消", "放弃", "退出"]):
        await matcher.finish("已退出历史上的今天推送时间设置")
    match = re.search(r"(\d*)[:：](\d*)", time)
    if match and match[1] and match[2]:
        if isinstance(event, GroupMessageEvent):
            calendar_subscribe("g_{}".format(event.group_id), int(match[1]), int(match[2]))
        else:
            calendar_subscribe("f_{}".format(event.user_id), int(match[1]), int(match[2]))
        await matcher.finish(f"历史上的今天的每日推送时间已设置为：{match[1]}:{match[2]}")
    else:
        state["max_times"] += 1
        if state["max_times"] >= 3:
            await matcher.finish("你的错误次数过多，已退出历史上的今天推送时间设置")
        await matcher.reject("设置时间失败，请输入正确的格式，格式为：小时:分钟")
