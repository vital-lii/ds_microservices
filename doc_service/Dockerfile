FROM python:3.11-slim

WORKDIR /app

#安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# 安装依赖文件
COPY requirements.txt ./
RUN pip install -i https://mirrors.aliyun.com/pypi/simple/ --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 暴露端口
EXPOSE 4000

# 推荐用环境变量或 docker-compose 传递 TOKEN 和 API KEY
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "4000"]
