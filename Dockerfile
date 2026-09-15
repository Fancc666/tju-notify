FROM python:3.12-slim

WORKDIR /app

# ddddocr / opencv 运行时需要的系统库
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libgl1 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv
RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
# 只安装依赖
RUN uv sync --frozen --no-dev

# 复制项目源码（含 start.sh）
COPY . .
RUN chmod +x start.sh

# 数据库目录，建议挂载出来持久化，否则重建容器会重新灌库
VOLUME ["/app/data"]

# 常驻调度：启动即检查一次，之后每小时检查
CMD ["./start.sh"]
