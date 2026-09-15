# tju-notify

天津大学统一门户（`f.tju.edu.cn`）**通知通告**监听器：定时拉取通知，与本地 SQLite 对比，发现新通知就入库并发邮件提醒。

## 工作流程

```
登录（CAS + 验证码 OCR + DES 加密）
      ↓ 复用 data/cache.json 里的 Cookie
【仅首次】库为空 -> 静默把当前通知全部入库，不发邮件
      ↓
POST /tp_up/up/messages/getAllPimList   （每次 30 条）
      ↓ 过滤 TYPE_ENGLISH_NAME == "Notice"（通知通告）
与 data/history.db 中已存在的 RESOURCE_ID 对比
      ↓ 有新增
入库 -> 按发布时间汇总 -> 发邮件
```

新通知的判断标准是 **RESOURCE_ID 没在库里出现过**，所以同一条通知不会重复推送；邮件发送失败也不会导致下轮重复发送（入库与发信是分开记录 `notified_at` 的）。

## 文件结构

| 路径 | 作用 |
| --- | --- |
| `main.py` | 入口：命令行、调度循环、会话获取 |
| `utils/api.py` | 通知接口请求与「通知通告」过滤 |
| `utils/db.py` | SQLite 建表与增删查（去重入库） |
| `utils/notify.py` | 单轮任务编排：对比、入库、拼邮件、发信 |
| `utils/login.py` | CAS 登录 |
| `utils/captcha.py` | ddddocr 验证码识别 |
| `utils/custom_des.py` | 登录密码所需的 DES 实现 |
| `utils/mail.py` | SMTP 发信 |
| `utils/EnvironTool.py` | `.env` 与系统环境变量统一读取 |
| `data/history.db` | 通知数据库（已 gitignore） |
| `data/cache.json` | 登录 Cookie 缓存（已 gitignore） |
| `data/sample_notices.json` | 本地测试样例数据 |

## 配置

复制 `.env.example` 为 `.env` 并填写：

```dotenv
USER_NAME = 学号
USER_PWD = 密码

SMTP_SERVER = smtp.qq.com      # 也兼容旧拼写 STMP_SERVER
SMTP_USER = you@qq.com
SMTP_PASSWORD = 授权码          # 注意是 SMTP 授权码，不是邮箱登录密码
SMTP_PORT = 587                # 465 走 SSL，其他端口走 STARTTLS
ADMIN_MAIL = you@qq.com

POLL_CRON = 0 * * * *          # 每小时整点；置空则用 POLL_INTERVAL_MINUTES
POLL_INTERVAL_MINUTES = 60
BOOTSTRAP_ON_START = 1         # 首次启动静默灌入历史通知，不发邮件
```

`POLL_CRON` 支持 `schedule` 库能力范围内的子集：`0 * * * *`（每小时第 0 分）、`*/30 * * * *`（每 30 分钟）、`30 9 * * *`（每天 09:30）；无法识别的表达式会退回按 `POLL_INTERVAL_MINUTES` 执行。

## 使用

```bash
# 安装依赖
uv sync

# 首次建表
python main.py --init-db

# 常驻调度：启动即检查一次，之后每小时检查（启动时会先静默灌入历史通知）
python main.py
# 或
./start.sh

# 只跑一次（适合配合系统 cron）
python main.py --once

# 只灌历史通知（不发邮件）
python main.py --bootstrap

# 查看库里最新 N 条
python main.py --recent 5
```

## 本地测试

### A. 不联网、不发信，验证完整判定链路

把「接口返回」打桩成样例数据，就能离线跑通「首次静默 -> 出现新通知 -> 发信 -> 不重复发」：

```python
import json
from pathlib import Path
from utils.EnvironTool import config

config["DB_PATH"] = "/tmp/tju-test.db"      # 用临时库，不动真实数据
import main
from utils import db, notify

main.get_session = lambda force_login=False: object()      # 跳过登录

api = json.loads(Path("data/sample_notices.json").read_text(encoding="utf-8"))[:2]
notify.fetch_notices_with_retry = lambda sess: api          # 打桩接口
sent = []
notify.send_info_mail = lambda subject, body: (sent.append(subject), True)[1]

db.init_db()
main.job()                       # 首次：静默入库，sent 仍为 0
main.job()                       # 无变化：不发信
api.append(dict(api[0], RESOURCE_ID="NEW-1", PIM_TITLE="模拟新通知"))
main.job()                       # 出现新通知：发 1 封
print("发信次数 =", len(sent), "| 标题 =", sent[-1])
print("库里行数 =", db.count_notices())
```

### B. 真实运行（会真的登录并发邮件）

```bash
python main.py --reset    # 清空库，模拟全新环境
python main.py --once     # 首跑：静默入库，不发邮件
python main.py --once     # 再跑：无新增，也不发邮件
python main.py --recent 5 # 查看库里数据
```

等真的有新通知出现时，下一轮就会发邮件。

> `--seed-sample` 只是往库里塞几条固定样例，方便你看数据和表结构。
> 因为它不在接口返回里，`check_once` 不会把它当成新通知，所以**不会触发邮件**。

## Docker

```bash
docker build -t tju-notify .
docker run -d --name tju-notify \
  --env-file .env \
  -v "$PWD/data:/app/data" \
  --restart unless-stopped \
  tju-notify
```

`/app/data` 一定要挂载出来，否则容器重建后数据库清空，会重新灌历史通知。

## 数据库表

`notices` 表主键为 `RESOURCE_ID`，字段与接口一一对应（`title`、`content`、`belong_unit_name`、`create_time` 等），另有 `created_at`（入库时间）与 `notified_at`（发信时间）。

## 注意事项

- 登录依赖 ddddocr 识别验证码，偶尔识别失败，代码会循环重试直到得到 4 位结果。
- 接口会话失效时会自动重新登录一次再重试。
- 首次启动默认静默灌入历史通知，避免一次性收到几十封邮件；想让首轮就推送可设 `BOOTSTRAP_ON_START=0`。
