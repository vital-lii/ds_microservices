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
import ast
from pathlib import Path
from fastapi import Request, Body
from typing import Optional, Dict, Any
from pydantic import BaseModel
import datetime
import asyncio
import json
import aiohttp

# 加载.env文件
load_dotenv(dotenv_path=Path(__file__).parent.parent / '.env')

# 读取token和API key
API_TOKEN = os.getenv("TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("doc_service.log")
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Document Service API",
    description="文档解析和分析服务",
    version="1.0.0"
)

class AnalysisResponse(BaseModel):
    text: str
    ast: Dict[str, Any]

class DeepSeekClient:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com/v1/chat/completions"

    async def analyze_code(self, code: str, prompt: str = None) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        if prompt:
            final_prompt = prompt + "\n" + code
        else:
            final_prompt = "Only output the final code. Do not include any explanation or reasoning. Output only a single code block.\n" + code
        payload = {
            "model": "deepseek-reasoner",
            "messages": [{"role": "user", "content": final_prompt}],
            "max_tokens": 2000
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=headers, json=payload, timeout=30) as response:
                    raw_text = await response.text()
                    logger.error(f"DeepSeek status: {response.status}")
                    logger.error(f"DeepSeek raw response: {raw_text}")
                    if response.status != 200:
                        logger.error(f"DeepSeek API错误 (状态码: {response.status}): {raw_text}")
                        return {"error": f"DeepSeek API错误: {raw_text}"}
                    try:
                        result = json.loads(raw_text)
                    except Exception as e:
                        logger.error(f"JSON解析失败: {e}")
                        return {"error": f"JSON解析失败: {e}, 原始内容: {raw_text}"}
                    if "choices" in result and result["choices"]:
                        return {"content": result["choices"][0]["message"]["content"]}
                    return result
        except Exception as e:
            logger.error(f"DeepSeek API调用失败: {e}")
            return {"error": str(e)}

def verify_token(token: str):
    """验证API Token

    Args:
        token (str): Bearer token

    Raises:
        HTTPException: 当token无效时抛出401错误
    """
    if token != API_TOKEN:
        logger.warning("Token校验失败")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )

def parse_ast(text: str) -> Dict[str, Any]:
    """解析文本的抽象语法树

    Args:
        text (str): 要解析的文本内容

    Returns:
        Dict[str, Any]: 解析后的AST结构

    Raises:
        Exception: 解析失败时抛出异常
    """
    try:
        # 尝试解析Python代码的AST
        tree = ast.parse(text)
        return {
            "type": "Module",
            "body": [{
                "type": node.__class__.__name__,
                "line": node.lineno if hasattr(node, 'lineno') else None,
                "col": node.col_offset if hasattr(node, 'col_offset') else None
            } for node in ast.walk(tree)]
        }
    except SyntaxError:
        # 如果不是Python代码，返回简单的文本结构分析
        lines = text.split('\n')
        return {
            "type": "Text",
            "statistics": {
                "lines": len(lines),
                "characters": len(text),
                "words": len(text.split()),
                "paragraphs": sum(1 for line in lines if line.strip())
            }
        }

class AnalyzeRequest(BaseModel):
    code: str = None
    use_deepseek: bool = False
    prompt: str = None  # 新增字段，允许用户自定义指令

@app.post("/extract", response_model=Dict[str, str])
async def extract_text(
    file: UploadFile = File(..., max_size=10_000_000),  # 限制10MB
    authorization: str = Header(None)
):
    """提取文档中的文本内容

    Args:
        file (UploadFile): 上传的文件（PDF/DOCX/MD）
        authorization (str): Bearer token

    Returns:
        Dict[str, str]: 提取的文本内容

    Raises:
        HTTPException: 文件处理失败时抛出相应的错误
    """
    # Token校验
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"}
        )
    token = authorization.split(" ")[1]
    verify_token(token)

    content = await file.read()
    text = ""

    logger.info(f"收到文件: {file.filename} ({len(content)/1024:.1f}KB)")

    try:
        if file.filename.endswith('.pdf'):
            reader = PyPDF2.PdfReader(io.BytesIO(content))
            for page in reader.pages:
                text += page.extract_text() or ""
        elif file.filename.endswith('.docx'):
            text = docx2txt.process(io.BytesIO(content))
        elif file.filename.endswith('.txt'):
            text = decode_text(content, encodings=['utf-8', 'gbk', 'latin-1'])
        elif file.filename.endswith('.sh'):
            text = decode_text(content, encodings=['utf-8'])
        elif file.filename.endswith('.yaml') or file.filename.endswith('.yml'):
            text = decode_text(content, encodings=['utf-8'])
        elif file.filename.endswith('.md'):
            # 尝试 utf-8 和 gbk 解码
            try:
                text = content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text = content.decode('gbk')
                except Exception as e:
                    logger.error(f"文件编码解析失败: {e}")
                    raise HTTPException(400, "Unsupported file encoding")
        else:
            supported_formats = ['.pdf', '.docx', '.md','.txt','.sh','.yaml','.yml']
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Supported formats: {', '.join(supported_formats)}"
            )
    except Exception as e:
        logger.error(f"文档解析失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Document parsing failed: {str(e)}"
        )

    # 简化文本，移除多余空白字符
    text = re.sub(r'\s+', ' ', text).strip()
    
    # 如果文本超过5000字符，记录日志
    if len(text) > 5000:
        logger.warning(f"文本内容已截断，原始长度: {len(text)}")
        text = text[:5000]
    
    logger.info(f"文档解析成功: {file.filename}, 长度: {len(text)}")
    return JSONResponse(content={"text": text})

@app.post("/v1/analyze", response_model=AnalysisResponse)
async def analyze_text(
    request: AnalyzeRequest,
    authorization: str = Header(None)
):
    code = request.code
    use_deepseek = request.use_deepseek
    prompt = request.prompt
    if not code:
        raise HTTPException(400, "需要提供文件或代码")

    # Token验证
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization",
            headers={"WWW-Authenticate": "Bearer"}
        )
    verify_token(authorization.split(" ")[1])

    try:
        text = code
        if use_deepseek:
            deepseek_client = DeepSeekClient()
            ds_result = await deepseek_client.analyze_code(text, prompt)
            return AnalysisResponse(text=text[:5000], ast=ds_result)
        else:
            ast_tree = parse_ast(text)
            return AnalysisResponse(text=text[:5000], ast=ast_tree)
    except Exception as e:
        logger.error(f"分析失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )

@app.get("/health")
def health():
    """健康检查接口

    Returns:
        Dict[str, str]: 服务状态信息
    """
    return {
        "status": "ok",
        "version": "1.0.0",
        "timestamp": datetime.datetime.now().isoformat()
    }