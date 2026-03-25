#!/usr/bin/env python3
"""
study-ingest Skill 本地测试脚本
"""

import asyncio
import json
from pathlib import Path

# 添加当前目录到 Python 路径
import sys
sys.path.insert(0, str(Path(__file__).parent))

from ingest import run_skill


async def test_ingest_concept():
    """测试概念输入"""
    print("=" * 60)
    print("测试 1: 学习新概念 - Transformer")
    print("=" * 60)
    
    result = await run_skill({
        "action": "ingest",
        "concept": "Transformer",
        "content": "今天学了 Transformer，它依赖自注意力机制",
        "user_id": "test_user"
    })
    
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


async def test_resume_session():
    """测试断点续传"""
    print("\n" + "=" * 60)
    print("测试 2: 恢复上次学习进度")
    print("=" * 60)
    
    result = await run_skill({
        "action": "resume",
        "user_id": "test_user"
    })
    
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


async def test_sensitive_info():
    """测试敏感信息检测"""
    print("\n" + "=" * 60)
    print("测试 3: 敏感信息检测")
    print("=" * 60)
    
    from ingest import StudyIngest
    
    ingest = StudyIngest("bolt://localhost:7687", "neo4j", "password")
    
    test_content = """
    我的 API key 是 sk-1234567890abcdefghijklmnop
    GitHub token: ghp_abcdefghijklmnopqrstuvwxyz1234567890
    邮箱：test@example.com
    电话：13800138000
    本地路径：/home/username/projects/my-project
    """
    
    sensitive = ingest._detect_sensitive_info(test_content)
    print(f"检测到 {len(sensitive)} 项敏感信息:")
    for item in sensitive:
        print(f"  - {item['type']}: {item['match'][:20]}...")
    
    redacted = ingest._redact_sensitive_info(test_content, sensitive)
    print("\n脱敏后内容:")
    print(redacted)
    
    ingest.close()
    return sensitive


async def main():
    """运行所有测试"""
    print("StudyEngine - study-ingest Skill 测试套件\n")
    
    try:
        # 测试 1: 概念输入
        await test_ingest_concept()
        
        # 测试 2: 断点续传
        await test_resume_session()
        
        # 测试 3: 敏感信息检测
        await test_sensitive_info()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
