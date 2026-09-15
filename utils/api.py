"""通知接口封装：拉取 tp_up 消息列表并过滤出「通知通告」。"""

from __future__ import annotations

import time
from typing import Any

import requests

from .EnvironTool import config
from .printer import print_flush, YELLOW, RESET

# 通知列表接口
LIST_URL = "https://f.tju.edu.cn/tp_up/up/messages/getAllPimList"

# 一次拉取多少条
LIMIT_SIZE = int(config.get("LIMIT_SIZE") or 30)
# 网络请求超时（秒）
REQUEST_TIMEOUT = int(config.get("REQUEST_TIMEOUT") or 20)
# 失败重试次数
MAX_RETRY = int(config.get("MAX_RETRY") or 3)


def is_notice(item: dict[str, Any]) -> bool:
    """判断一条记录是不是「通知通告」。

    按 TYPE_NAME 判断。
    """
    return "通知" in str(item.get("TYPE_NAME") or "")


def fetch_notices(session: requests.Session) -> list[dict[str, Any]]:
    """请求一次接口，返回过滤后的通知通告列表。

    网络/接口异常会抛出 requests 或 ValueError，由调用方决定如何处理。
    """
    response = session.post(
        LIST_URL,
        json={"LIMIT_SIZE": LIMIT_SIZE, "PIM_TITLE": ""},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    response.encoding = "utf-8"
    data = response.json()
    if not isinstance(data, list):
        raise ValueError(f"接口返回格式异常: {type(data).__name__}")
    return [item for item in data if isinstance(item, dict) and is_notice(item)]


def fetch_notices_with_retry(
    session: requests.Session, retries: int = MAX_RETRY
) -> list[dict[str, Any]]:
    """带指数退避的重试版本；重试耗尽后抛出最后一次异常。"""
    last_error: Exception | None = None
    for attempt in range(1, max(1, retries) + 1):
        try:
            return fetch_notices(session)
        except Exception as e:  # noqa: BLE001 - 统一重试
            last_error = e
            if attempt < retries:
                wait = 2 ** (attempt - 1)
                print_flush(
                    f"{YELLOW}[api] 第 {attempt} 次请求失败（{e}），{wait}s 后重试{RESET}"
                )
                time.sleep(wait)
    assert last_error is not None
    raise last_error
