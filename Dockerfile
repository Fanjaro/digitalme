# 使用 Python 3.12  slim 基础镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 替换Debian源为国内阿里云源，加快apt安装速度
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources \
    && sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 配置pip国内源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn

# 复制 requirements.txt（单独复制这层，利用Docker缓存，不用每次改代码都重新装依赖）
COPY requirements.txt .

# 安装 Python 依赖，包含uvicorn的WebSocket支持
RUN pip install --no-cache-dir -r requirements.txt uvicorn[standard]

# 复制项目代码
COPY . .

# 暴露端口（根据实际需要调整，比如API服务端口）
EXPOSE 8000

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 默认启动命令（FastAPI服务入口在server.py）
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]