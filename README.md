# DS-microservices 项目说明

## 1. 项目简介

本项目为基于 FastAPI 的文档解析与 OCR 微服务，支持 PDF/DOCX 文档内容提取，具备 API Token 鉴权，适合本地开发和云端部署。

---

## 2. 目录结构

```
DS-microservices/
├── doc_service/         # 文档解析微服务
│   ├── main.py
│   └── ...
├── ocr_service/         # OCR 图像识别微服务
├── scripts/             # 部署脚本
├── shared/              # 通用配置
├── venv/                # Python 虚拟环境（建议本地开发用）
├── docker-compose.yml   # Docker 一键部署配置
└── README.md            # 项目说明
```

---

## 3. 环境准备与依赖安装

### 3.1 创建并激活 venv 虚拟环境

```bash
# 进入项目目录
cd DS-microservices
# 创建虚拟环境
python -m venv venv
# 激活虚拟环境（Windows）
.\venv\Scripts\activate
# 激活虚拟环境（Linux/macOS）
source venv/bin/activate
```

### 3.2 使用阿里云镜像安装依赖

```bash
# 进入 doc_service 目录
cd doc_service
# 安装依赖
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

---

## 4. .env 文件配置

在 `doc_service` 目录下新建 `.env` 文件，内容示例：

```
TOKEN=你的自定义高强度Token
DEEPSEEK_API_KEY=你的DeepSeek API Key
```

- TOKEN 用于 API 鉴权，建议用 16 位以上随机字符串。
- DEEPSEEK_API_KEY 预留给后续 DeepSeek API 调用。

---

## 5. FastAPI 服务启动方法

### 5.1 启动服务

```bash
# 进入 doc_service 目录，激活 venv 后运行：
uvicorn main:app --reload --port 4000
```

- `--reload` 适合开发调试，代码变动自动重启。
- 服务启动后访问 http://localhost:4000/docs 查看 API 文档。

### 5.2 关闭服务

- 在运行 FastAPI 的终端窗口按 `Ctrl+C` 即可。

---

## 6. curl/Postman 测试方法

### 6.1 curl 测试

```bash
curl -X POST "http://localhost:4000/extract" -H "Authorization: Bearer 你的TOKEN" -F "file=@test.docx"
```

- 替换 `你的TOKEN` 为 .env 文件中的 TOKEN。
- 替换 `test.docx` 为你要上传的文件名。

### 6.2 Postman 测试

1. 新建 POST 请求，URL 填 `http://localhost:4000/extract`
2. Body 选 `form-data`，添加 `file` 字段，类型选 File，上传文件
3. Headers 添加 `Authorization: Bearer 你的TOKEN`
4. 发送请求，查看返回结果

---

## 7. 常见问题与排查

- **报错 `Form data requires "python-multipart" to be installed`**
  - 解决：`pip install python-multipart`
- **curl 报 `Bad hostname`**
  - 解决：Windows 下 curl 命令要写成一行，不要用 `\` 换行
- **端口无法连接**
  - 检查 FastAPI 服务是否已启动，端口是否正确
- **Token 校验失败**
  - 检查 Authorization header 是否正确，Token 是否与 .env 一致

---

## 8. 关闭/重启服务说明

- 关闭服务：在运行 FastAPI 的终端按 `Ctrl+C`
- 重启服务：重新运行 `uvicorn main:app --reload --port 4000`
- 开发时建议服务一直开启，便于随时测试

---

如需部署到云服务器、docker-compose 配置、API 安全加固等帮助，详见后续文档或联系开发者。
