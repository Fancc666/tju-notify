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

新通知的判断标准是 **RESOURCE_ID 没在库里出现过**，所以同一条通知不会重复推送；邮件发送失败也不会导致下轮重复发送。

## 文件结构

| 路径 | 作用 |
| --- | --- |
| `main.py` | 入口：命令行、调度循环、会话获取 |
| `utils/api.py` | 通知接口请求与「通知通告」过滤 |
| `utils/db.py` | SQLite 建表与增删查 |
| `utils/notify.py` | 单轮任务编排：对比、入库、拼邮件、发信 |
| `utils/login.py` | CAS 登录 |
| `utils/captcha.py` | 验证码识别 |
| `utils/custom_des.py` | 登录密码所需的 DES 实现 |
| `utils/mail.py` | SMTP 发信 |
| `utils/EnvironTool.py` | `.env` 与系统环境变量统一读取 |
| `data/history.db` | 通知数据库 |
| `data/cache.json` | 登录 Cookie 缓存 |
| `data/sample_notices.json` | 本地测试样例数据 |

## 配置

复制 `.env.example` 为 `.env` 并按照提示填写环境变量。

`POLL_CRON` 支持常用子集：`0 * * * *`（每小时第 0 分）、`*/30 * * * *`（每 30 分钟）、`30 9 * * *`（每天 09:30）、`0 6-23 * * *`（6-23 点每小时）、`0 6,12,18 * * *`（每天 3 个整点）；无法识别的表达式会退回按 `POLL_INTERVAL_MINUTES` 执行（会打印提示）。

## 使用

### 开发调试

主要命令

```bash
# 安装依赖
uv sync

# 首次建表
python main.py --init-db

# 启动运行
./start.sh
```

其他命令

```bash
# 只跑一次（适合配合系统 cron）
python main.py --once

# 只灌历史通知（不发邮件）
python main.py --bootstrap

# 查看库里最新 N 条
python main.py --recent 5
```

### 使用Docker

```bash
docker build -t tju-notify .
docker run -d --name tju-notify \
  --env-file .env \
  -v "$PWD/data:/app/data" \
  tju-notify
```

`/app/data` 强烈建议挂载卷。

## 数据库表

`notices` 表主键为 `RESOURCE_ID`，字段与接口一一对应（`title`、`content`、`belong_unit_name`、`create_time` 等），另有 `created_at`（入库时间）与 `notified_at`（发信时间）。

## 特殊提示

请合理使用项目功能，不要为学校服务器带来负担。

使用MIT协议开源。
