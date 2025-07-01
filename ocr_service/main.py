import os
from fastapi import FastAPI, UploadFile, File, HTTPException, Header, status
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from PIL import Image
import pytesseract
import io
import logging
import winreg
from pathlib import Path

# 加载.env文件
load_dotenv(dotenv_path=Path(__file__).parent.parent / '.env')

# 读取token
API_TOKEN = os.getenv("TOKEN")

# 调试：验证 TOKEN 加载
print(f"🔍 OCR服务 - 当前工作目录: {os.getcwd()}")
print(f"🔍 OCR服务 - .env 文件是否存在: {Path('.env').exists()}")
print(f"🔍 OCR服务 - TOKEN 值: {API_TOKEN}")
print(f"🔍 OCR服务 - TOKEN 长度: {len(API_TOKEN) if API_TOKEN else 0}")
print("-" * 50)

# 日志配置
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI()

def get_tesseract_path():
    """自动定位 Tesseract 的可执行文件"""
    # 1. 检查符号链接路径
    symlink_path = Path("C:/Tesseract/tesseract.exe")
    if symlink_path.exists():
        return str(symlink_path)
    
    # 2. 检查标准安装路径
    standard_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
    ]
    for path in standard_paths:
        if Path(path).exists():
            return path
    
    # 3. 从注册表获取安装路径
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\\Tesseract-OCR") as key:
            install_dir = winreg.QueryValueEx(key, "InstallPath")[0]
            exe_path = Path(install_dir) / "tesseract.exe"
            if exe_path.exists():
                return str(exe_path)
    except Exception:
        pass
    
    # 4. 尝试系统 PATH（最后手段）
    try:
        pytesseract.get_tesseract_version()
        return "tesseract"
    except pytesseract.TesseractNotFoundError:
        raise EnvironmentError(
            "Tesseract OCR 未找到。请确保已安装并创建符号链接："
            "mklink /D C:\\Tesseract \"C:\\Program Files\\Tesseract-OCR\""
        )

# 初始化设置
pytesseract.pytesseract.tesseract_cmd = get_tesseract_path()
print(f"使用的 Tesseract 路径: {pytesseract.pytesseract.tesseract_cmd}")

def verify_token(token: str):
    if token != API_TOKEN:
        logging.warning("Token校验失败")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

@app.post("/ocr")
async def ocr_image(
    file: UploadFile = File(...),
    authorization: str = Header(None)
):
    # Token校验
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.split(" ")[1]
    verify_token(token)

    try:
        image = Image.open(io.BytesIO(await file.read()))
        # 图像优化：缩放大图
        if max(image.width, image.height) > 2000:
            image.thumbnail((2000, 2000))
        # OCR识别（中英文）
        text = pytesseract.image_to_string(image, lang='chi_sim+eng')
    except Exception as e:
        logging.error(f"OCR识别失败: {e}")
        raise HTTPException(status_code=500, detail="OCR failed")

    text = text.strip()[:2000]  # 限制返回长度
    logging.info(f"OCR识别成功: {file.filename}, 长度: {len(text)}")
    return JSONResponse(content={"text": text})

# 可选：健康检查
@app.get("/health")
def health():
    return {"status": "ok"}
