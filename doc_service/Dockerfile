FROM python:3.11-slim

WORKDIR /app

# 切换 apt 源为阿里云，加速系统依赖下载
RUN sed -i 's@http://deb.debian.org@https://mirrors.aliyun.com@g' /etc/apt/sources.list

# 安装系统依赖和 Tesseract OCR（含中文包）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmagic1 \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
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
