import asyncio
import json
import os
import aiohttp
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 调试：验证 .env 文件加载
print(f"🔍 当前工作目录: {os.getcwd()}")
print(f"🔍 .env 文件是否存在: {Path('.env').exists()}")
print(f"🔍 TOKEN 值: {os.getenv('TOKEN')}")
print(f"🔍 DEEPSEEK_API_KEY 值: {os.getenv('DEEPSEEK_API_KEY')[:10] if os.getenv('DEEPSEEK_API_KEY') else 'None'}...")
print("-" * 50)

class DeepSeekAPI:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
    
    async def call(self, prompt: str):
        """单次调用"""
        messages = [{"role": "user", "content": prompt}]
        return await self.call_with_history(messages)
    
    async def call_with_history(self, messages: List[Dict]):
        """带历史记录的调用"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "deepseek-coder",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=headers, json=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"DeepSeek API错误 (状态码: {response.status}): {error_text}")
                    
                    result = await response.json()
                    if "choices" not in result or not result["choices"]:
                        print(f"⚠️ DeepSeek API返回异常: {result}")
                        return "DeepSeek API调用失败，无法获取响应"
                    
                    return result["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"❌ DeepSeek API调用失败: {e}")
            return f"DeepSeek API调用失败: {str(e)}"

class CursorLikeCLI:
    def __init__(self):
        self.deepseek_api = DeepSeekAPI()
        self.conversation_history = []
        self.current_context = {}
        self.doc_service_url = "http://localhost:4000"
        self.ocr_service_url = "http://localhost:4001"
        self.token = os.getenv("TOKEN")
        
        # 如果 .env 文件没有加载成功，手动设置 TOKEN
        if not self.token:
            print("⚠️ 从 .env 文件加载 TOKEN 失败，使用默认值")
            self.token = "1234569696Kq!"  # 替换为你的实际 TOKEN
        
        # 验证 TOKEN 配置
        if not self.token:
            print("❌ 警告：TOKEN 环境变量未设置！")
            print("   请在 .env 文件中设置 TOKEN=你的Token")
        else:
            print(f"✅ TOKEN 已加载: {self.token[:10]}...")
        
        # 验证 DeepSeek API Key
        if not os.getenv("DEEPSEEK_API_KEY"):
            print("❌ 警告：DEEPSEEK_API_KEY 环境变量未设置！")
            print("   请在 .env 文件中设置 DEEPSEEK_API_KEY=你的API Key")
        else:
            print("✅ DeepSeek API Key 已加载")
    
    async def upload_and_process(self, file_path: str):
        """上传并预处理文件"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            print(f"❌ 文件不存在：{file_path}")
            return
        
        print(f"📁 正在处理文件：{file_path}")
        
        if file_path.suffix.lower() in ['.py', '.js', '.java', '.cpp', '.c', '.go', '.md']:
            # 代码文件或 Markdown
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.current_context = {
                "type": "code" if file_path.suffix.lower() != '.md' else "markdown",
                "language": file_path.suffix[1:],
                "content": content,
                "file_path": str(file_path)
            }
            
        elif file_path.suffix.lower() in ['.png', '.jpg', '.jpeg']:
            # 图片文件 - 调用 OCR 服务
            content = await self._call_ocr_service(file_path)
            self.current_context = {
                "type": "image",
                "content": content,
                "file_path": str(file_path)
            }
            
        elif file_path.suffix.lower() in ['.pdf', '.docx']:
            # 文档文件 - 调用文档服务
            content = await self._call_doc_service(file_path)
            self.current_context = {
                "type": "document",
                "content": content,
                "file_path": str(file_path)
            }
        else:
            print(f"❌ 不支持的文件类型：{file_path.suffix}")
            return
        
        # 初始化对话
        await self.initialize_conversation()
    
    async def _call_ocr_service(self, file_path: Path):
        """调用 OCR 服务"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            data = aiohttp.FormData()
            data.add_field('file', open(file_path, 'rb'), filename=file_path.name)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.ocr_service_url}/ocr", headers=headers, data=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"OCR服务错误 (状态码: {response.status}): {error_text}")
                    
                    result = await response.json()
                    if "text" not in result:
                        print(f"⚠️ OCR服务返回异常: {result}")
                        return "OCR识别失败，无法获取文本内容"
                    return result["text"]
        except Exception as e:
            print(f"❌ OCR服务调用失败: {e}")
            return f"OCR处理失败: {str(e)}"
    
    async def _call_doc_service(self, file_path: Path):
        """调用文档服务"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            data = aiohttp.FormData()
            data.add_field('file', open(file_path, 'rb'), filename=file_path.name)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.doc_service_url}/extract", headers=headers, data=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"文档服务错误 (状态码: {response.status}): {error_text}")
                    
                    result = await response.json()
                    if "text" not in result:
                        print(f"⚠️ 文档服务返回异常: {result}")
                        return "文档解析失败，无法获取文本内容"
                    return result["text"]
        except Exception as e:
            print(f"❌ 文档服务调用失败: {e}")
            return f"文档处理失败: {str(e)}"
    
    async def initialize_conversation(self):
        """初始化与 DeepSeek 的对话"""
        context_info = self.current_context
        
        if context_info["type"] in ["code", "markdown"]:
            prompt = f"""
            我已经上传了一个 {context_info['language']} 文件：{context_info['file_path']}
            
            文件内容：
            ```{context_info['language']}
            {context_info['content']}
            ```
            
            请分析这个文件，并告诉我你理解了什么。你可以：
            1. 解释代码的主要功能（如果是代码文件）
            2. 总结文档内容（如果是 Markdown 文档）
            3. 指出潜在的问题
            4. 提供完整的改进建议，包括代码和文档
            
            现在你可以回答我的问题或接受我的指令。
            """
        else:
            prompt = f"""
            我已经上传了一个文件：{context_info['file_path']}
            
            提取的内容：
            {context_info['content']}
            
            请分析这个内容，并告诉我你理解了什么。现在你可以回答我的问题或接受我的指令。
            """
        
        response = await self.deepseek_api.call(prompt)
        self.conversation_history.append({"role": "assistant", "content": response})
        print(f"\n🤖 DeepSeek: {response}\n")
    
    async def chat(self, user_input: str):
        """多轮对话"""
        # 构建对话历史
        messages = []
        
        # 添加上下文
        context_info = self.current_context
        if context_info["type"] in ["code", "markdown"]:
            messages.append({
                "role": "system",
                "content": f"你是一个专业的代码助手，正在分析一个 {context_info['language']} 文件。"
            })
            messages.append({
                "role": "user", 
                "content": f"文件内容：\n```{context_info['language']}\n{context_info['content']}\n```"
            })
        else:
            messages.append({
                "role": "system",
                "content": "你是一个专业的文档分析助手。"
            })
            messages.append({
                "role": "user",
                "content": f"文档内容：\n{context_info['content']}"
            })
        
        # 添加对话历史
        messages.extend(self.conversation_history)
        
        # 添加当前用户输入
        messages.append({"role": "user", "content": user_input})
        
        # 调用 DeepSeek API
        response = await self.deepseek_api.call_with_history(messages)
        
        # 更新对话历史
        self.conversation_history.append({"role": "user", "content": user_input})
        self.conversation_history.append({"role": "assistant", "content": response})
        
        return response
    
    async def interactive_mode(self):
        """交互模式"""
        print("🚀 欢迎使用 Cursor-like CLI！")
        print("📁 请先上传文件：")
        print("   支持：.py, .js, .java, .cpp, .c, .go, .md, .png, .jpg, .jpeg, .pdf, .docx")
        print("   命令：upload <文件路径>")
        print("   退出：quit 或 exit")
        
        while True:
            try:
                user_input = input("\n>>> ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 再见！")
                    break
                
                if user_input.startswith('upload '):
                    # 上传文件
                    file_path = user_input[7:].strip()
                    await self.upload_and_process(file_path)
                elif user_input.startswith('clear'):
                    # 清除对话历史
                    self.conversation_history = []
                    self.current_context = {}
                    print("🧹 对话历史已清除")
                else:
                    # 普通对话
                    if not self.current_context:
                        print("❌ 请先上传文件！使用 'upload <文件路径>' 命令")
                        continue
                    
                    response = await self.chat(user_input)
                    print(f"\n🤖 DeepSeek: {response}\n")
                    
            except KeyboardInterrupt:
                print("\n👋 再见！")
                break
            except Exception as e:
                print(f"❌ 错误：{e}")

# 使用示例
if __name__ == "__main__":
    cli = CursorLikeCLI()
    asyncio.run(cli.interactive_mode())
