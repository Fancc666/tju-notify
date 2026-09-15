"""轮询任务：拉取通知 -> 与库中数据对比 -> 新通知入库 -> 发邮件汇总。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from . import db
from .api import fetch_notices_with_retry
from .EnvironTool import config
from .mail import send_info_mail
from .printer import print_flush, RED, GREEN, YELLOW, CYAN, RESET

# 邮件正文里单条内容的截断长度，0 表示不截断
MAIL_CONTENT_LIMIT = int(config.get("MAIL_CONTENT_LIMIT") or 2000)
# 入库正文长度上限，0 表示不限制
STORE_CONTENT_LIMIT = int(config.get("STORE_CONTENT_LIMIT") or 0)

CST = timezone(timedelta(hours=8))


def format_ms(value: Any) -> str:
    """毫秒时间戳 -> 'YYYY-MM-DD HH:MM:SS'（北京时间），空值返回 '-'。"""
    if value in (None, "", 0, "0"):
        return "-"
    try:
        return datetime.fromtimestamp(int(value) / 1000, CST).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError, OSError):
        return "-"


def _trim(text: Any, limit: int) -> str:
    text = str(text or "").strip()
    if limit and len(text) > limit:
        return text[:limit] + "……（已截断）"
    return text


def _build_mail(notices: list[dict[str, Any]]) -> tuple[str, str]:
    """拼邮件标题与正文。"""
    first = notices[0]
    if len(notices) == 1:
        subject = f"新通知：{str(first.get('PIM_TITLE') or '').strip()}"
    else:
        subject = f"新增 {len(notices)} 条通知（最新：{str(first.get('PIM_TITLE') or '').strip()}）"

    lines: list[str] = [
        f"检测到 {len(notices)} 条新通知，按发布时间从新到旧：",
        "",
    ]
    for index, item in enumerate(notices, start=1):
        lines.append(f"{index}. {str(item.get('PIM_TITLE') or '').strip()}")
        lines.append(f"   发布单位：{item.get('BELONG_UNIT_NAME') or '-'}")
        lines.append(f"   发布人　：{item.get('CREATE_USER_NAME') or '-'}")
        lines.append(f"   发布时间：{format_ms(item.get('CREATE_TIME'))}")
        lines.append(f"   类型　　：{item.get('TYPE_NAME') or '-'}")
        lines.append(
            f"   详情　　：https://f.tju.edu.cn/tp_up/view?m=up#act=portal/viewNotice&resourceId={item.get('RESOURCE_ID') or ''}"
        )
        content = _trim(item.get("PIM_CONTENT"), MAIL_CONTENT_LIMIT)
        if content:
            lines.append("   正文　　：")
            lines.extend(f"     {line}" for line in content.splitlines() or [content])
        lines.append("")
    lines.append(f"—— 由 tju-notify 于 {datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S')} 自动发送")
    return subject, "\n".join(lines)


def check_once(session: requests.Session, session_provider=None) -> int:
    """执行一轮检查，返回本次新增并已入库的通知条数。

    session_provider: 可选的无参函数，返回新的 requests.Session，
    用于在会话失效时重新登录后重试一次。
    """
    print_flush(f"{CYAN}[poll] {datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S')} 开始检查通知{RESET}")

    try:
        notices = fetch_notices_with_retry(session)
    except Exception as e:  # noqa: BLE001 - 单轮失败不影响后续调度
        if session_provider is None:
            print_flush(f"{RED}[poll] 拉取通知失败：{e}{RESET}")
            raise
        print_flush(f"{YELLOW}[poll] 拉取通知失败（{e}），尝试重新登录{RESET}")
        session = session_provider()
        notices = fetch_notices_with_retry(session)

    if not notices:
        print_flush(f"{YELLOW}[poll] 本轮没有拿到通知通告{RESET}")
        return 0

    # 已入库的 resource_id 集合，查找出新的id
    known = db.get_existing_ids([str(item.get("RESOURCE_ID") or "") for item in notices])
    new_items = [
        item for item in notices if str(item.get("RESOURCE_ID") or "") not in known
    ]

    if not new_items:
        print_flush(f"{GREEN}[poll] 共 {len(notices)} 条通知，没有新增{RESET}")
        return 0

    # 按发布时间从新到旧处理
    new_items.sort(key=lambda x: int(x.get("CREATE_TIME") or 0), reverse=True)

    if STORE_CONTENT_LIMIT:
        for item in new_items:
            item["PIM_CONTENT"] = _trim(item.get("PIM_CONTENT"), STORE_CONTENT_LIMIT)

    inserted = db.insert_notices(new_items)
    print_flush(f"{GREEN}[poll] 新增 {len(inserted)} 条通知，已入库：{inserted}{RESET}")

    if not inserted:
        return 0

    subject, body = _build_mail(new_items)
    if send_info_mail(subject, body):
        db.mark_notified(inserted)
    else:
        print_flush(f"{YELLOW}[poll] 邮件未发送成功，通知已入库，下一轮不会重复推送{RESET}")
    return len(inserted)


def bootstrap(session: requests.Session) -> int:
    """首次运行：把历史通知静默入库，不发邮件，避免启动即刷屏。

    只有在库里一条数据都没有时才会执行。
    """
    if db.count_notices() > 0:
        return 0
    # 如果首次运行
    print_flush(f"{YELLOW}[init] 数据库为空，静默灌入历史通知{RESET}")
    notices = fetch_notices_with_retry(session)
    if not notices:
        return 0
    inserted = db.insert_notices(notices)
    print_flush(f"{GREEN}[init] 历史通知入库 {len(inserted)} 条{RESET}")
    return len(inserted)
