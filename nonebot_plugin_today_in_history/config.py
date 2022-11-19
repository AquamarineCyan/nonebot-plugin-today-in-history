from typing import Union

from pydantic import BaseSettings


class Config(BaseSettings):
    history_qq_friends: list[int] = []  # 格式[123,456]
    history_qq_groups: list[int] = []  # 格式[123,456]
    # 兼容v0.0.8及以下
    history_inform_time: Union[str, list] = None  # 默认早上7:35

    class Config:
        extra = "ignore"
