import os
from fastapi import FastAPI, UploadFile, File, HTTPException, Header, status
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import docx2txt
import PyPDF2
import io
import re
import logging
import markdown
from pathlib import Path

# 加载.env文件
load_dotenv(dotenv_path=Path(__file__).parent.parent / '.env')

# 读取token和API key
API_TOKEN = os.getenv("TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# 日志配置
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s") 

app = FastAPI()

def verify_token(token: str):
    if token != API_TOKEN:
        logging.warning("Token校验失败")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

@app.post("/extract")
async def extract_text(
    file: UploadFile = File(..., max_size=10_000_000),  # 限制10MB
    authorization: str = Header(None)
):
    # Token校验
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split(" ")[1]
    verify_token(token)

    content = await file.read()
    text = ""

    logging.info(f"收到文件: {file.filename} ({len(content)/1024:.1f}KB)")

    try:
        if file.filename.endswith('.pdf'):
            reader = PyPDF2.PdfReader(io.BytesIO(content))
            for page in reader.pages:
                text += page.extract_text() or ""
        elif file.filename.endswith('.docx'):
            text = docx2txt.process(io.BytesIO(content))
        elif file.filename.endswith('.md'):
            # 尝试 utf-8 和 gbk 解码
            try:
                text = content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text = content.decode('gbk')
                except Exception:
                    raise HTTPException(400, "Unsupported file encoding")
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")
    except Exception as e:
        logging.error(f"文档解析失败: {e}")
        raise HTTPException(status_code=500, detail="Document parsing failed")

    # 简化文本
    text = re.sub(r'\s+', ' ', text)[:5000]
    logging.info(f"文档解析成功: {file.filename}, 长度: {len(text)}")
    return JSONResponse(content={"text": text})

@app.get("/health")
def health():
    return {"status": "ok"}