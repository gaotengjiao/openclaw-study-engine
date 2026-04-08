import httpx
import json
from abc import ABC, abstractmethod


class BaseLLMAdapter(ABC):
    """适配器基类 (类似 Java 的 Interface)"""

    @abstractmethod
    async def generate_tree(self, prompt: str, model_name: str) -> str:
        pass


class DashScopeAdapter(BaseLLMAdapter):
    """阿里灵积 (通义千问) 适配器"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

    async def generate_tree(self, prompt: str, model_name: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-SSE": "disable"
        }
        # 阿里灵积的标准格式比较复杂，注意嵌套
        payload = {
            "model": model_name or "qwen-turbo",
            "input": {
                "messages": [
                    {"role": "system", "content": "你是一个 JSON 知识图谱生成助手。"},
                    {"role": "user", "content": prompt}
                ]
            },
            "parameters": {
                "result_format": "message"
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self.url, headers=headers, json=payload)
            resp.raise_for_status()
            result = resp.json()
            # 阿里返回的结构是 output -> choices -> message -> content
            return result.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", "{}")


class OpenAIAdapter(BaseLLMAdapter):
    """OpenAI 标准适配器 (支持 DeepSeek, ChatGPT 等)"""

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')

    async def generate_tree(self, prompt: str, model_name: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_name or "gpt-3.5-turbo",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            result = resp.json()
            return result.get("choices", [{}])[0].get("message", {}).get("content", "{}")


class DifyAdapter(BaseLLMAdapter):
    """Dify 知识中台适配器"""

    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')

    async def generate_tree(self, prompt: str, model_name: str) -> str:
        """
        注意：Dify 的 401 常见于使用个人密钥而非应用密钥。
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # 核心逻辑：这里我建议使用 completion-messages 接口
        # 因为生成知识树通常是单次任务，不需要上下文对话流
        url = f"{self.base_url}/completion-messages"

        payload = {
            "inputs": {},  # 这里可以传入你 Dify 工作流预设的变量
            "query": prompt,
            "response_mode": "blocking",
            "user": "adam_study_engine"
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload, headers=headers)

                # 如果还是 401，这里会抛出异常，方便我们在控制台看到明确错误
                if resp.status_code == 401:
                    print("❌ [Dify 401] 认证失败！请检查 Dify 应用内的 'API 密钥'，不是个人设置里的。")

                resp.raise_for_status()
                result = resp.json()
                return result.get("answer", "{}")
        except httpx.HTTPStatusError as e:
            # 捕获 404，如果 completion 接口不存在，尝试回退到 chat 接口
            if e.response.status_code == 404:
                # 重新尝试 chat-messages
                return await self._retry_with_chat(prompt, headers)
            raise e

    async def _retry_with_chat(self, prompt: str, headers: dict) -> str:
        """回退方案：调用聊天接口"""
        url = f"{self.base_url}/chat-messages"
        payload = {
            "inputs": {},
            "query": prompt,
            "response_mode": "blocking",
            "conversation_id": "",  # 开启新对话
            "user": "adam_study_engine"
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json().get("answer", "{}")