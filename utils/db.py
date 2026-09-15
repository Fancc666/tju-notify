"""SQLite 持久化层：存放通知通告。

只保存 `TYPE_ENGLISH_NAME == "Notice"` 的通知，用 RESOURCE_ID 作为业务唯一键去重。
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

from .EnvironTool import config
from .printer import print_flush, YELLOW, RESET

# 项目根目录下的 data/history.db（docker volume 也挂这里）
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "history.db"

# 接口返回的字段 -> 数据库列名
FIELD_MAP = {
    "RESOURCE_ID": "resource_id",
    "PIM_TITLE": "title",
    "PIM_CONTENT": "content",
    "CONTENT_URL": "content_url",
    "CONTENT_TYPE_ID": "content_type_id",
    "TYPE_NAME": "type_name",
    "TYPE_ENGLISH_NAME": "type_english_name",
    "BELONG_UNIT_ID": "belong_unit_id",
    "BELONG_UNIT_NAME": "belong_unit_name",
    "CREATE_USER_UNIT_NAME": "create_user_unit_name",
    "CREATE_USER_NAME": "create_user_name",
    "CREATE_ID_NUMBER": "create_id_number",
    "AUDIT_ID_NUMBER": "audit_id_number",
    "CREATE_TIME": "create_time",
    "AUDIT_TIME": "audit_time",
    "MODIFY_TIME": "modify_time",
    "REJECT_TIME": "reject_time",
    "END_TOP_TIME": "end_top_time",
    "IS_TOP": "is_top",
    "IS_READ": "is_read",
    "IS_EMERGENCY_LINK": "is_emergency_link",
    "IS_AUDIT": "is_audit",
    "ROWNUM": "rownum",
}

TABLE_SQL = """
CREATE TABLE IF NOT EXISTS notices (
    resource_id           TEXT PRIMARY KEY,        -- 通知唯一标识
    title                 TEXT NOT NULL,           -- 标题
    content               TEXT,                    -- 正文
    content_url           TEXT,                    -- 正文 json 地址
    content_type_id       TEXT,
    type_name             TEXT,                    -- 类型名（通知通告）
    type_english_name     TEXT,                    -- Notice
    belong_unit_id        TEXT,                    -- 发布单位 id
    belong_unit_name      TEXT,                    -- 发布单位
    create_user_unit_name TEXT,
    create_user_name      TEXT,                    -- 发布人
    create_id_number      TEXT,
    audit_id_number       TEXT,
    create_time           INTEGER,                 -- 毫秒时间戳
    audit_time            INTEGER,
    modify_time           INTEGER,
    reject_time           INTEGER,
    end_top_time          INTEGER,
    is_top                TEXT,
    is_read               TEXT,
    is_emergency_link     TEXT,
    is_audit              TEXT,
    rownum                INTEGER,
    created_at            TEXT,                    -- 本地入库时间（ISO8601）
    notified_at           TEXT
);

CREATE INDEX IF NOT EXISTS idx_notices_create_time ON notices (create_time DESC);
CREATE INDEX IF NOT EXISTS idx_notices_created_at  ON notices (created_at DESC);
"""


def get_db_path() -> Path:
    """数据库路径，可通过环境变量 DB_PATH 覆盖。"""
    raw = config.get("DB_PATH") or ""
    return Path(raw) if raw else DEFAULT_DB_PATH


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")

@contextmanager
def connect() -> Generator[sqlite3.Connection]:
    """打开连接（自动建目录、提交/回滚、关闭）。"""
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """建表（幂等），并清理残留的 -wal/-shm 之外的空库文件。"""
    with connect() as conn:
        conn.executescript(TABLE_SQL)


def _row_from_notice(notice: dict[str, Any]) -> dict[str, Any]:
    row = {col: notice.get(src) for src, col in FIELD_MAP.items()}
    row["resource_id"] = str(row.get("resource_id") or "").strip()
    row["title"] = (row.get("title") or "").strip()
    row["created_at"] = _now()
    return row


def notice_exists(resource_id: str) -> bool:
    with connect() as conn:
        cur = conn.execute(
            "SELECT 1 FROM notices WHERE resource_id = ? LIMIT 1", (str(resource_id),)
        )
        return cur.fetchone() is not None


def get_latest_notice() -> dict[str, Any] | None:
    """库里最新的一条（先按 create_time，再按入库时间）。"""
    with connect() as conn:
        cur = conn.execute(
            "SELECT * FROM notices ORDER BY create_time DESC, created_at DESC LIMIT 1"
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_existing_ids(resource_ids: list[str]) -> set[str]:
    """在给定 id 列表中，返回已存在于库里的那些（一次查询，避免 N+1）。"""
    ids = [str(r) for r in resource_ids if str(r or "").strip()]
    if not ids:
        return set()
    found: set[str] = set()
    with connect() as conn:
        # SQLite 参数上限约 999，分批查询
        for i in range(0, len(ids), 500):
            chunk = ids[i : i + 500]
            placeholders = ",".join("?" * len(chunk))
            cur = conn.execute(
                f"SELECT resource_id FROM notices WHERE resource_id IN ({placeholders})",
                chunk,
            )
            found.update(str(r["resource_id"]) for r in cur.fetchall())
    return found


def get_latest_create_time() -> int:
    with connect() as conn:
        cur = conn.execute("SELECT MAX(create_time) AS t FROM notices")
        row = cur.fetchone()
        return int(row["t"]) if row and row["t"] is not None else 0


def insert_notices(notices: list[dict[str, Any]]) -> list[str]:
    """批量入库，已存在的跳过。返回真正插入的 resource_id 列表。"""
    inserted: list[str] = []
    rows = [_row_from_notice(n) for n in notices]
    with connect() as conn:
        for row in rows:
            if not row["resource_id"]:
                # 如果没有resource_id就不存了
                continue
            cur = conn.execute(
                """
                INSERT INTO notices (
                    resource_id, title, content, content_url, content_type_id,
                    type_name, type_english_name, belong_unit_id, belong_unit_name,
                    create_user_unit_name, create_user_name, create_id_number,
                    audit_id_number, create_time, audit_time, modify_time,
                    reject_time, end_top_time, is_top, is_read, is_emergency_link,
                    is_audit, rownum, created_at, notified_at
                ) VALUES (
                    :resource_id, :title, :content, :content_url, :content_type_id,
                    :type_name, :type_english_name, :belong_unit_id, :belong_unit_name,
                    :create_user_unit_name, :create_user_name, :create_id_number,
                    :audit_id_number, :create_time, :audit_time, :modify_time,
                    :reject_time, :end_top_time, :is_top, :is_read, :is_emergency_link,
                    :is_audit, :rownum, :created_at, :notified_at
                )
                ON CONFLICT(resource_id) DO NOTHING
                """,
                {**row, "notified_at": None},
            )
            if cur.rowcount:
                inserted.append(row["resource_id"])
    return inserted


def mark_notified(resource_ids: list[str]) -> int:
    """标记这些通知已经发过邮件。"""
    if not resource_ids:
        return 0
    ts = _now()
    with connect() as conn:
        cur = conn.executemany(
            "UPDATE notices SET notified_at = ? WHERE resource_id = ?",
            [(ts, str(rid)) for rid in resource_ids],
        )
        return cur.rowcount


def count_notices() -> int:
    with connect() as conn:
        cur = conn.execute("SELECT COUNT(*) AS c FROM notices")
        return int(cur.fetchone()["c"])


def get_recent_notices(limit: int = 10) -> list[dict[str, Any]]:
    with connect() as conn:
        cur = conn.execute(
            "SELECT * FROM notices ORDER BY create_time DESC, created_at DESC LIMIT ?",
            (int(limit),),
        )
        return [dict(r) for r in cur.fetchall()]


if __name__ == "__main__":
    init_db()
    print_flush(f"{YELLOW}[db] {get_db_path()} 已初始化，现有 {count_notices()} 条通知{RESET}")
