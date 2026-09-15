FROM python:3.12-slim

# ============================================================
# 国内镜像配置（可用 --build-arg 覆盖）这里默认走镜像源了( ^_^ )
#   docker build \
#     --build-arg APT_MIRROR=mirrors.aliyun.com \
#     --build-arg PIP_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple \
#     -t tju-notify .
# ============================================================

ARG APT_MIRROR=mirrors.tuna.tsinghua.edu.cn
ARG PIP_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple
ARG UV_VERSION=0.9.27

ENV PIP_INDEX_URL=${PIP_INDEX} \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_DEFAULT_INDEX=${PIP_INDEX} \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

WORKDIR /app

# 把 Debian 源换成国内镜像。
# 说明：去掉 ddddocr 之后已经没有需要系统库的依赖了，
# 这里装 ca-certificates 是为了保证 HTTPS 访问，同时让换源对后续加包也有意义。
RUN set -eux; \
    find /etc/apt -type f \( -name '*.list' -o -name '*.sources' \) \
        -exec sed -i \
            -e "s|http://deb.debian.org|https://${APT_MIRROR}|g" \
            -e "s|http://security.debian.org|https://${APT_MIRROR}|g" \
            {} + ; \
    echo 'Acquire::Retries "3";' > /etc/apt/apt.conf.d/99retries; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates; \
    rm -rf /var/lib/apt/lists/*

# 安装 uv
RUN pip install --no-cache-dir "uv==${UV_VERSION}"

COPY pyproject.toml uv.lock ./
# 依赖层单独缓存
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# 复制项目源码（含 start.sh）
COPY . .
RUN chmod +x start.sh

# 数据库目录，建议挂载出来持久化，否则重建容器会重新灌库
VOLUME ["/app/data"]

# 常驻调度：启动即检查一次，之后每小时检查
CMD ["./start.sh"]
