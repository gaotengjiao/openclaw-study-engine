import re
import json
from typing import Dict
from app.core.config import settings
from .llm.adapters import DashScopeAdapter, OpenAIAdapter, DifyAdapter

class LLMProcessor:
    def __init__(self):
        self.sensitive_patterns = []
        rules = settings.get("sensitivity", {}).get("rules", [])
        for r in rules:
            if isinstance(r, dict):
                self.sensitive_patterns.append({
                    "type": r.get("name"),
                    "pattern": re.compile(r.get("pattern"))
                })
        self.adapter = self._init_adapter()

    def _init_adapter(self):
        cfg = settings.get("llm", {}).get("settings", {})
        provider = cfg.get("provider", "dify")
        api_key = cfg.get("api_key")
        base_url = cfg.get("base_url", "http://127.0.0.1/v1")

        if provider == "dify":
            return DifyAdapter(api_key, base_url)
        return OpenAIAdapter(api_key, base_url)

    async def get_completed_tree(self, subject: str, concept: str, user_content: str = "") -> Dict:
        prompt = f"请为 {subject} 领域的概念 {concept} 生成标准 JSON 格式的知识树。上下文：{user_content}"
        try:
            # 透传参数到 kwargs
            res_text = await self.adapter.generate_tree(
                prompt,
                "",
                subject=subject,
                concept=concept
            )
            return self._parse_json(res_text, concept)
        except Exception as e:
            print(f"⚠️ [LLMProcessor Error] {e}")
            return {"name": concept, "children": []}

    def _parse_json(self, text: str, concept: str) -> Dict:
        try:
            return json.loads(text)
        except:
            try:
                match = re.search(r'\{.*\}', text, re.DOTALL)
                if match: return json.loads(match.group())
            except: pass
            return {"name": concept, "children": []}