# OpenClaw LLM 集成指南

## 背景

`_ai_complete_knowledge()` 函数目前返回示例数据，需要替换为真实的 OpenClaw LLM 调用。

---

## 方式一：使用 `sessions_spawn`（推荐）

在 OpenClaw 环境中，最可靠的方式是创建子代理来处理 LLM 调用：

### 修改 `ingest.py`

```python
async def _ai_complete_knowledge(self, concept_name: str) -> Dict:
    """调用 OpenClaw LLM 补全知识结构"""
    
    # 方式一：使用 sessions_spawn
    from openclaw.sessions import sessions_spawn
    
    prompt = f"""请为「{concept_name}」生成 2-3 级知识树，每级 3-5 个子节点，输出 JSON 格式。

要求：
1. 第一级：3-5 个主要分支（如核心原理、应用场景、相关技术等）
2. 第二级：每个分支下 2-3 个子概念
3. 输出纯 JSON，不要 markdown 格式

示例输出：
{{
    "concept": "Transformer",
    "children": [
        {{
            "name": "自注意力机制",
            "children": [
                {{"name": "QKV 矩阵计算"}},
                {{"name": "缩放点积注意力"}},
                {{"name": "多头注意力"}}
            ]
        }}
    ]
}}
"""
    
    # 创建子代理任务
    result = await sessions_spawn(
        task=prompt,
        model="dashscope/qwen3.5-plus",  # 或你的默认模型
        mode="run",
        cleanup="delete"
    )
    
    # 解析响应
    import json
    import re
    
    response = result.get("response", "")
    
    # 尝试提取 JSON
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if json_match:
        return json.loads(json_match.group())
    else:
        return json.loads(response)
```

---

## 方式二：使用 OpenClaw 工具接口

如果你的 OpenClaw 版本支持直接工具调用：

```python
async def _ai_complete_knowledge(self, concept_name: str) -> Dict:
    """调用 OpenClaw 工具接口"""
    
    # 使用 OpenClaw 的工具调用接口
    # 具体 API 根据你的 OpenClaw 版本可能不同
    
    from openclaw.tools import call_tool
    
    response = await call_tool(
        tool="llm",
        model="dashscope/qwen3.5-plus",
        prompt=f"请为「{concept_name}」生成 2-3 级知识树..."
    )
    
    import json
    return json.loads(response)
```

---

## 方式三：使用 HTTP API（如果可用）

如果 OpenClaw 暴露了 HTTP API：

```python
import aiohttp

async def _ai_complete_knowledge(self, concept_name: str) -> Dict:
    """调用 OpenClaw HTTP API"""
    
    url = "http://localhost:8080/api/llm/chat"  # 示例 URL
    
    payload = {
        "model": "dashscope/qwen3.5-plus",
        "messages": [
            {"role": "user", "content": f"请为「{concept_name}」生成 2-3 级知识树..."}
        ]
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            data = await resp.json()
            import json
            return json.loads(data["response"])
```

---

## 实际步骤

### 1. 确认你的 OpenClaw 版本

```bash
openclaw --version
```

### 2. 查看可用的 LLM 调用方式

```bash
openclaw tools list
```

或查看文档：

```bash
cat /root/.openclaw/workspace/docs/*.md | grep -i llm
```

### 3. 选择合适的方式

| 方式 | 适用场景 | 复杂度 |
|-----|---------|-------|
| sessions_spawn | 推荐，最稳定 | 低 |
| 工具接口 | 如果 OpenClaw 支持 | 中 |
| HTTP API | 自定义集成 | 高 |

### 4. 修改 `ingest.py`

替换 `_ai_complete_knowledge()` 函数中的示例代码。

### 5. 测试

```bash
cd /root/.openclaw/workspace/skills/study-ingest
python test_ingest.py
```

---

## 调试技巧

### 如果 LLM 返回格式不正确

添加重试逻辑：

```python
async def _ai_complete_knowledge(self, concept_name: str, max_retries: int = 3) -> Dict:
    for attempt in range(max_retries):
        try:
            response = await call_llm(...)
            return json.loads(response)
        except json.JSONDecodeError:
            if attempt == max_retries - 1:
                # 返回默认结构
                return {"concept": concept_name, "children": []}
            continue
```

### 如果响应太慢

添加超时：

```python
import asyncio

async def _ai_complete_knowledge(self, concept_name: str) -> Dict:
    try:
        return await asyncio.wait_for(
            self._call_llm(concept_name),
            timeout=30.0  # 30 秒超时
        )
    except asyncio.TimeoutError:
        # 返回默认结构
        return {"concept": concept_name, "children": []}
```

---

## 下一步

1. 确认你的 OpenClaw 环境支持哪种 LLM 调用方式
2. 替换 `_ai_complete_knowledge()` 中的代码
3. 运行测试验证
4. 如果需要帮助，告诉我你的 OpenClaw 版本和可用工具
