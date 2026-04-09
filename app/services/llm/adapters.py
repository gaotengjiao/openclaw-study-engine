import httpx
import json
import re
from .base import BaseLLMAdapter


class DashScopeAdapter(BaseLLMAdapter):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

    async def generate_tree(self, prompt: str, model_name: str, **kwargs) -> str: return "{}"


class OpenAIAdapter(BaseLLMAdapter):
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')

    async def generate_tree(self, prompt: str, model_name: str, **kwargs) -> str: return "{}"


class DifyAdapter(BaseLLMAdapter):
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')

    async def generate_tree(self, prompt: str, model_name: str, **kwargs) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # 严格对齐 Dify 聊天助手需要的 inputs 变量
        inputs = {
            "concept": kwargs.get("concept", "未知概念"),
            "subject": kwargs.get("subject", "通用学科")
        }

        payload = {
            "inputs": inputs,
            "query": prompt,
            "response_mode": "blocking",
            "user": "adam_37",
            "conversation_id": ""
        }

        url = f"{self.base_url}/chat-messages"

        async with httpx.AsyncClient(timeout=60.0) as client:
            print(f"🚀 [Dify Request] Sending to {url} with variables: {inputs}")
            try:
                resp = await client.post(url, json=payload, headers=headers)

                if resp.status_code != 200:
                    print(f"❌ [Dify API Error] Status: {resp.status_code}, Body: {resp.text}")
                    # 即使报错也返回一个基础 JSON，防止上层解析崩溃
                    return json.dumps({"name": inputs["concept"], "children": []})

                result = resp.json()
                raw_answer = result.get("answer", "")

                # 强力清洗 Markdown 和杂质文字
                clean_json = re.sub(r'```json\s*|\s*```', '', raw_answer).strip()
                match = re.search(r'\{.*\}', clean_json, re.DOTALL)
                return match.group() if match else clean_json

            except Exception as e:
                print(f"❌ [Dify Adapter Exception] {str(e)}")
                return json.dumps({"name": kwargs.get("concept", "Error"), "children": []})