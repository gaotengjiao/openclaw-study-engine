import json
import re
from typing import Dict, List, Any
# 确保 config 已经 load 成功
from app.core.config import settings
from .llm.adapters import DashScopeAdapter, OpenAIAdapter, DifyAdapter


class LLMProcessor:
    def __init__(self):
        """
        初始化：加载安全规则与动态选择模型适配器
        """
        # --- 【核心修正】 ---
        # 将 Pydantic 对象转为 Python 字典，这样才能使用 .get()
        # model_dump() 是 Pydantic v2 的写法，如果是 v1 请用 .dict()
        self.conf = settings.model_dump() if hasattr(settings, 'model_dump') else settings.dict()

        # 1. 预编译脱敏规则
        self.sensitive_patterns = []
        rules = self.conf.get("sensitivity", {}).get("rules", [])
        for r in rules:
            self.sensitive_patterns.append({
                "type": r["name"],
                "pattern": re.compile(r["pattern"])
            })

        # 2. 适配器工厂逻辑
        self.adapter = self._init_adapter()

    def _init_adapter(self):
        """根据配置动态创建适配器实例"""
        llm_cfg = self.conf.get("llm", {}).get("settings", {})
        provider = llm_cfg.get("provider", "dify")
        api_key = llm_cfg.get("api_key")

        if provider == "dify":
            base_url = llm_cfg.get("base_url", "https://api.dify.ai/v1")
            return DifyAdapter(api_key, base_url)
        elif provider == "dashscope":
            return DashScopeAdapter(api_key)
        elif provider == "openai":
            base_url = llm_cfg.get("base_url", "https://api.openai.com/v1")
            return OpenAIAdapter(api_key, base_url)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    def _redact_content(self, content: str) -> str:
        """执行内容脱敏"""
        if not content:
            return ""
        redacted = content
        for p in self.sensitive_patterns:
            redacted = p["pattern"].sub(f"<{p['type'].upper()}>", redacted)
        return redacted

    async def get_completed_tree(self, subject: str, concept: str, user_content: str = "") -> Dict:
        """
        核心业务流：策略加载 -> 脱敏 -> 适配器调用 -> 解析
        """
        # 1. 动态加载学科 Prompt 策略
        policies = self.conf.get("llm", {}).get("subject_policies", {})
        policy = policies.get(subject, policies.get("default", {}))

        # 2. 脱敏参考内容
        safe_content = self._redact_content(user_content)

        # 3. 构造 Meta-Prompt
        prompt = f"""
        角色设定：{policy.get('guidance', '')}
        任务：请为「{subject}」学科中的概念「{concept}」生成 {policy.get('level_depth', 2)} 级知识树。
        用户参考上下文：{safe_content}

        要求：
        1. 必须输出纯 JSON 格式。
        2. 根节点名称必须为 "{concept}"。
        3. 结构：{{"name": "{concept}", "children": [{{ "name": "...", "children": [] }}]}}
        """

        # 4. 执行多模型适配调用
        try:
            llm_cfg = self.conf.get("llm", {}).get("settings", {})
            model_name = llm_cfg.get("default_model")
            response_text = await self.adapter.generate_tree(prompt, model_name)
            return self._parse_json(response_text, concept)
        except Exception as e:
            print(f"[LLM Error] 调用失败: {str(e)}")
            return {"name": concept, "children": []}

    def _parse_json(self, text: str, concept: str) -> Dict:
        """鲁棒解析 LLM 返回的 JSON"""
        try:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            json_str = match.group() if match else text
            return json.loads(json_str)
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"[Parser Error] 无法解析 JSON: {str(e)}")
            return {"name": concept, "children": []}