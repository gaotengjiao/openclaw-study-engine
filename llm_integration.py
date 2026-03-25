#!/usr/bin/env python3
"""
OpenClaw LLM 集成示例 - 用于知识补全
"""

import json
import asyncio
from typing import Dict, Optional


async def call_openclaw_llm(prompt: str, model: str = "dashscope/qwen3.5-plus") -> str:
    """
    通过 OpenClaw 调用 LLM
    
    在 OpenClaw Skill 中，你可以：
    1. 使用 sessions_spawn 创建子代理来处理 LLM 调用
    2. 或直接使用 OpenClaw 提供的工具接口
    
    这里展示两种方式
    """
    
    # 方式一：通过 sessions_spawn 调用（推荐用于复杂任务）
    # 需要在 OpenClaw 主进程中调用，示例：
    """
    from openclaw.sessions import spawn
    
    result = await spawn(
        task=f"请为这个概念生成 2-3 级知识树：{concept_name}",
        model=model,
        mode="run"
    )
    return result.response
    """
    
    # 方式二：直接调用 HTTP API（如果 OpenClaw 暴露了 API）
    # 这需要你知道 OpenClaw 的 API endpoint
    
    # 方式三：使用 OpenClaw 的 web_fetch 或自定义工具
    # 这需要配置 MCP 工具
    
    # 临时示例：返回模拟数据（实际使用时替换为真实调用）
    print(f"[LLM 调用] Prompt: {prompt[:100]}...")
    print(f"[LLM 调用] Model: {model}")
    
    # TODO: 替换为真实的 OpenClaw LLM 调用
    # 以下是示例响应结构
    return json.dumps({
        "concept": "示例概念",
        "children": [
            {"name": "子概念 1", "children": []},
            {"name": "子概念 2", "children": []}
        ]
    }, ensure_ascii=False)


async def complete_knowledge_tree(concept_name: str) -> Dict:
    """
    调用 LLM 补全知识结构
    
    Args:
        concept_name: 概念名称
        
    Returns:
        知识树 JSON 结构
    """
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
    
    response = await call_openclaw_llm(prompt)
    
    try:
        knowledge_tree = json.loads(response)
        return knowledge_tree
    except json.JSONDecodeError:
        # 如果 LLM 返回的不是纯 JSON，尝试提取 JSON 部分
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            # 返回默认结构
            return {
                "concept": concept_name,
                "children": [
                    {"name": f"{concept_name}核心原理", "children": []},
                    {"name": f"{concept_name}应用场景", "children": []},
                    {"name": f"{concept_name}相关技术", "children": []}
                ]
            }


if __name__ == "__main__":
    # 测试
    result = asyncio.run(complete_knowledge_tree("Transformer"))
    print(json.dumps(result, indent=2, ensure_ascii=False))
