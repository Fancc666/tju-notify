# 天津大学通知通告监听器
#
# 用法：
#   python main.py              # 启动调度：启动时先检查一次，之后每小时检查一次
#   python main.py --once       # 只检查一次（适合配合系统 cron 使用）
#   python main.py --bootstrap  # 只做首次静默灌库（不发邮件）
#   python main.py --recent 5   # 查看库里最新的 5 条通知
#   python main.py --init-db    # 只建表
#   python main.py --seed-sample# 写入本地样例通知，便于测试
#   python main.py --reset      # 清空 notices 表，便于重新测试「首次运行」
#
# 相关环境变量见 .env.example
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

from utils import db
from utils.EnvironTool import config
from utils.login import LoginLoader
from utils.notify import bootstrap, check_once
from utils.printer import print_flush, CYAN, GREEN, RED, RESET, YELLOW

cache_file = Path(__file__).parent / "data" / "cache.json"


def _new_session() -> requests.Session:
    """完整登录一次，并返回带登录态的 session。"""
    loader = LoginLoader(config.get("USER_NAME", ""), config.get("USER_PWD", ""))
    login_sess = loader.login()
    new_cookies = login_sess.cookies.get_dict()
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(new_cookies))
    return login_sess


def get_session(force_login: bool = False) -> requests.Session:
    """拿到可用的 session：优先复用 data/cache.json 里的 Cookie，失效则重新登录。"""
    if force_login:
        return _new_session()

    if cache_file.is_file():
        sess = requests.session()
        sess.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.76",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Origin": "https://f.tju.edu.cn",
                "Referer": "https://f.tju.edu.cn/tp_up/view?m=up",
            }
        )
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cookies = json.loads(f.read())
            for k, v in cookies.items():
                sess.cookies.set(k, v)
            home_response = sess.get(
                "https://f.tju.edu.cn/tp_up/view?m=up#act=portal/viewhome",
                timeout=15,
            )
            LoginLoader._ensure_login_success(home_response)
            print_flush(f"{GREEN}[session] 复用 Cookie 缓存成功{RESET}")
            return sess
        except Exception as e:  # noqa: BLE001 - 缓存不可用则退回登录
            print_flush(f"{YELLOW}[session] Cookie 缓存不可用（{e}），重新登录{RESET}")

    return _new_session()


def job() -> None:
    """单轮任务：保证 session 可用 -> 首次静默灌库 -> 检查新通知。

    只要数据库为空（首次运行），就先静默把当前接口返回的通知入库、不发邮件，
    之后的每一轮才只针对真正的新通知发信。调度模式和 --once 都走这里。
    """
    sess = get_session()

    if str(config.get("BOOTSTRAP_ON_START") or "1") == "1":
        bootstrap(sess)  # 库里已有数据时内部直接返回，不会重复灌

    check_once(sess, session_provider=lambda: get_session(force_login=True))


def _parse_cron_field(field: str, low: int, high: int) -> int | None:
    """解析单个 cron 字段，返回确定的值；'*' 或非法值返回 None。"""
    field = field.strip()
    if field == "*":
        return None
    if not field.isdigit():
        return None
    value = int(field)
    return value if low <= value <= high else None


def apply_schedule(schedule) -> None:
    """根据 POLL_CRON / POLL_INTERVAL_MINUTES 注册定时任务。

    支持 schedule 库自带能力范围内的 cron 子集：
      * * * * * 形式的「分 时 日 月 周」，其中日/月/周必须是 *，
      分钟可以用 */N 表示“每 N 分钟”，或 分+时 都是具体数字表示“每天几点几分”。
    其余写法（以及 POLL_CRON=""）退回按 POLL_INTERVAL_MINUTES 的固定间隔。
    """
    cron = config.get("POLL_CRON")
    cron = "0 * * * *" if cron is None else str(cron).strip()

    if cron:
        parts = cron.split()
        if len(parts) == 5 and all(p.strip() == "*" for p in parts[2:]):
            minute_field, hour_field = parts[0].strip(), parts[1].strip()
            # */N -> 每 N 分钟
            if minute_field.startswith("*/") and minute_field[2:].isdigit():
                step = int(minute_field[2:])
                if step > 0:
                    schedule.every(step).minutes.do(_safe_job)
                    print_flush(f"{CYAN}[scheduler] 已启动：每 {step} 分钟检查一次（cron: {cron}）{RESET}")
                    return
            minute = _parse_cron_field(minute_field, 0, 59)
            hour = _parse_cron_field(hour_field, 0, 23)
            if minute is not None and hour is not None:
                when = f"{hour:02d}:{minute:02d}"
                schedule.every().day.at(when).do(_safe_job)
                print_flush(f"{CYAN}[scheduler] 已启动：每天 {when} 检查一次（cron: {cron}）{RESET}")
                return
            if minute is not None and hour_field == "*":
                schedule.every().hour.at(f":{minute:02d}").do(_safe_job)
                print_flush(f"{CYAN}[scheduler] 已启动：每小时第 {minute} 分钟检查一次（cron: {cron}）{RESET}")
                return
        print_flush(
            f"{YELLOW}[scheduler] cron 表达式 {cron!r} 超出支持范围（支持 '0 * * * *'、'*/30 * * * *'、'30 9 * * *'），改按固定间隔{RESET}"
        )

    every = int(config.get("POLL_INTERVAL_MINUTES") or 60)
    schedule.every(every).minutes.do(_safe_job)
    print_flush(f"{CYAN}[scheduler] 已启动：每 {every} 分钟检查一次{RESET}")


def run_scheduler() -> None:
    """注册定时任务，启动时先跑一次（含首次静默灌库），然后常驻循环。"""
    import time

    import schedule  # 延迟导入，--once / --recent 等模式无需该依赖

    apply_schedule(schedule)

    db.init_db()

    # 启动时先跑一轮；失败不退出，交给后续调度重试
    _safe_job()

    while True:
        schedule.run_pending()
        time.sleep(30)


def _safe_job() -> None:
    """包一层异常保护，保证调度循环不会被单次失败打断。"""
    try:
        job()
    except Exception as e:  # noqa: BLE001
        print_flush(f"{RED}[scheduler] 本轮任务异常：{e}{RESET}")


def seed_sample(no_email: bool = True) -> int:
    """把 data/sample_notices.json 里的样例通知写入数据库，用于本地测试。

    只写入「通知通告」类型；已存在的 resource_id 会自动跳过。
    """
    sample_file = Path(__file__).parent / "data" / "sample_notices.json"
    if not sample_file.is_file():
        print_flush(f"{RED}[seed] 找不到样例文件：{sample_file}{RESET}")
        return 1

    from utils.api import is_notice

    with open(sample_file, "r", encoding="utf-8") as f:
        raw = json.load(f)
    samples = [item for item in raw if is_notice(item)]
    inserted = db.insert_notices(samples)
    print_flush(
        f"{GREEN}[seed] 样例 {len(samples)} 条，新入库 {len(inserted)} 条：{inserted}{RESET}"
    )
    if inserted and no_email:
        print_flush(
            f"{YELLOW}[seed] 已跳过邮件；样例只是便于查看数据/表结构，"
            f"不会触发邮件（它不在接口返回里）{RESET}"
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="天津大学通知通告监听器")
    parser.add_argument("--once", action="store_true", help="只检查一次后退出")
    parser.add_argument("--bootstrap", action="store_true", help="静默灌入历史通知后退出")
    parser.add_argument("--recent", type=int, metavar="N", help="打印库里最新 N 条通知后退出")
    parser.add_argument("--init-db", action="store_true", help="只建表后退出")
    parser.add_argument(
        "--seed-sample", action="store_true", help="写入本地样例通知（便于测试，不发邮件）"
    )
    parser.add_argument(
        "--reset", action="store_true", help="清空 notices 表（会丢失已记录的通知，谨慎使用）"
    )
    args = parser.parse_args()

    db.init_db()

    if args.reset:
        with db.connect() as conn:
            removed = conn.execute("DELETE FROM notices").rowcount
        print_flush(f"{YELLOW}[db] 已清空 notices 表，删除 {removed} 行{RESET}")
        return 0

    if args.init_db:
        print_flush(f"{GREEN}[db] 建表完成：{db.get_db_path()}{RESET}")
        return 0

    if args.seed_sample:
        return seed_sample()

    if args.recent is not None:
        rows = db.get_recent_notices(args.recent)
        print_flush(f"{CYAN}共 {db.count_notices()} 条，展示最新 {len(rows)} 条：{RESET}")
        for row in rows:
            print_flush(f"  [{row['create_time']}] {row['title']} —— {row['belong_unit_name']}")
        return 0

    if args.bootstrap:
        bootstrap(get_session())
        return 0

    if args.once:
        job()
        return 0

    run_scheduler()
    return 0


if __name__ == "__main__":
    sys.exit(main())
