#!/usr/bin/env python3
"""
study-ingest Skill - 知识输入与结构化核心逻辑
"""

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Neo4j 驱动（需要安装 neo4j 包）
from neo4j import GraphDatabase

# 配置
CONFIG_PATH = Path(__file__).parent / "config.yaml"
DB_PATH = Path(__file__).parent / "study_engine.db"
MEMORY_PATH = Path(__file__).parent.parent.parent / "memory"


class StudyIngest:
    """知识输入与结构化处理器"""
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.sqlite_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._init_sqlite()
        
    def _init_sqlite(self):
        """初始化 SQLite 表结构"""
        cursor = self.sqlite_conn.cursor()
        
        # 学习进度表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_progress (
                concept_id TEXT PRIMARY KEY,
                concept_name TEXT NOT NULL,
                mastery_score REAL DEFAULT 0,
                weight INTEGER DEFAULT 0,
                label TEXT DEFAULT 'New',
                last_reviewed DATE,
                next_review DATE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 版本快照表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS concept_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                concept_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                understanding TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (concept_id) REFERENCES learning_progress(concept_id)
            )
        """)
        
        # 会话状态表（断点续传）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                last_concept TEXT,
                last_stage TEXT,
                weaknesses TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.sqlite_conn.commit()
    
    async def ingest_concept(self, concept_name: str, content: str = "", user_id: str = "default") -> Dict:
        """
        输入一个新概念，自动补全知识结构并存入数据库
        
        Args:
            concept_name: 概念名称
            content: 用户提供的初始内容（可选）
            user_id: 用户标识
            
        Returns:
            处理结果字典
        """
        # Step 1: AI 知识补全（2-3 级扩展）
        knowledge_tree = await self._ai_complete_knowledge(concept_name)
        
        # Step 2: 敏感信息检测
        sensitive_info = self._detect_sensitive_info(content)
        if sensitive_info:
            content = self._redact_sensitive_info(content, sensitive_info)
        
        # Step 3: 存入 Neo4j 知识图谱
        self._save_to_neo4j(knowledge_tree)
        
        # Step 4: 初始化 SQLite 学习进度
        self._init_learning_progress(knowledge_tree, user_id)
        
        # Step 5: 保存会话状态（断点续传）
        self._save_session_state(user_id, concept_name, "定义阶段", [])
        
        return {
            "status": "success",
            "concept": concept_name,
            "knowledge_tree": knowledge_tree,
            "sensitive_info_found": len(sensitive_info) if sensitive_info else 0,
            "next_step": "开始费曼学习法：请用 3 句话解释核心定义"
        }
    
    async def _ai_complete_knowledge(self, concept_name: str) -> Dict:
        """
        调用 OpenClaw LLM 补全 2-3 级知识结构
        使用 sessions_spawn 创建子代理任务
        Fallback 策略：优先 Qwen，失败时自动切换到 MiniMax
        """
        import json
        import re
        from openclaw.sessions import sessions_spawn
        
        prompt = f"""请为「{concept_name}」生成 2-3 级知识树，每级 3-5 个子节点，输出 JSON 格式。

要求：
1. 第一级：3-5 个主要分支（如核心原理、应用场景、相关技术等）
2. 第二级：每个分支下 2-3 个子概念
3. 输出纯 JSON，不要 markdown 格式，不要多余解释

示例输出格式：
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
        
        # Fallback 模型列表
        model_fallbacks = [
            "dashscope/qwen3.5-plus",  # 优先 Qwen
            "minimax/MiniMax-M2.5",    # 备选 MiniMax
        ]
        
        for model in model_fallbacks:
            try:
                print(f"[LLM 尝试] 使用模型：{model}")
                
                # 创建子代理任务
                result = await sessions_spawn(
                    task=prompt,
                    model=model,
                    mode="run",
                    cleanup="delete",
                    timeoutSeconds=60
                )
                
                response = result.get("response", "")
                
                # 尝试提取 JSON
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    knowledge_tree = json.loads(json_match.group())
                    print(f"[LLM 成功] 模型：{model}")
                    return knowledge_tree
                else:
                    knowledge_tree = json.loads(response)
                    print(f"[LLM 成功] 模型：{model}")
                    return knowledge_tree
                    
            except Exception as e:
                print(f"[LLM 失败] 模型 {model}: {e}")
                continue
        
        # 所有模型都失败，返回默认结构
        print(f"[LLM 全部失败] 返回默认结构")
        return {
            "concept": concept_name,
            "children": [
                {"name": f"{concept_name}核心原理", "children": []},
                {"name": f"{concept_name}应用场景", "children": []},
                {"name": f"{concept_name}相关技术", "children": []}
            ]
        }
    
    def _detect_sensitive_info(self, content: str) -> List[Dict]:
        """
        检测敏感信息
        
        Returns:
            敏感信息列表，每项包含 {type, pattern, match}
        """
        if not content:
            return []
        
        sensitive_patterns = [
            {"type": "api_key", "pattern": r"sk-[a-zA-Z0-9]{20,}"},
            {"type": "github_token", "pattern": r"ghp_[a-zA-Z0-9]{36}"},
            {"type": "aws_key", "pattern": r"AKIA[0-9A-Z]{16}"},
            {"type": "password", "pattern": r"password\s*[=:]\s*['\"]?[^\s'\"]+"},
            {"type": "email", "pattern": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"},
            {"type": "phone", "pattern": r"1[3-9]\d{9}"},
            {"type": "local_path", "pattern": r"/home/[a-zA-Z0-9_]+/|C:\\Users\\[a-zA-Z0-9_]+\\"},
        ]
        
        found = []
        for item in sensitive_patterns:
            matches = re.findall(item["pattern"], content, re.IGNORECASE)
            for match in matches:
                found.append({
                    "type": item["type"],
                    "pattern": item["pattern"],
                    "match": match
                })
        
        return found
    
    def _redact_sensitive_info(self, content: str, sensitive_info: List[Dict]) -> str:
        """脱敏处理"""
        for item in sensitive_info:
            if item["type"] in ["api_key", "github_token", "aws_key"]:
                content = content.replace(item["match"], "<REDACTED>")
            elif item["type"] == "password":
                # 使用普通字符串替换而非正则，避免转义问题
                match = item["match"]
                if "=" in match or ":" in match:
                    # 保留密码前的部分
                    for sep in ["=", ":"]:
                        if sep in match:
                            prefix, pwd = match.rsplit(sep, 1)
                            content = content.replace(match, prefix + sep + "${PASSWORD}")
                            break
                else:
                    content = content.replace(match, "${PASSWORD}")
            elif item["type"] in ["email", "phone"]:
                content = content.replace(item["match"], "<PERSONAL_INFO>")
            elif item["type"] == "local_path":
                content = re.sub(
                    r"/home/[a-zA-Z0-9_]+/",
                    "<PROJECT_ROOT>/",
                    content
                )
                content = re.sub(
                    r"C:\\\\Users\\\\[a-zA-Z0-9_]+\\\\",
                    "<PROJECT_ROOT>\\\\",
                    content
                )
        
        return content
    
    def _save_to_neo4j(self, knowledge_tree: Dict):
        """将知识树存入 Neo4j"""
        with self.neo4j_driver.session() as session:
            self._create_concept_node(session, knowledge_tree, parent_name=None)
    
    def _create_concept_node(self, session, node: Dict, parent_name: Optional[str]):
        """递归创建概念节点"""
        concept_name = node["concept"] if "concept" in node else node["name"]
        
        # 创建当前节点
        session.run("""
            MERGE (c:Concept {name: $name})
            SET c.updated_at = datetime()
            SET c.version = coalesce(c.version, 0) + 1
        """, name=concept_name)
        
        # 创建依赖关系
        if parent_name:
            session.run("""
                MATCH (parent:Concept {name: $parent})
                MATCH (child:Concept {name: $child})
                MERGE (child)-[:DEPENDS_ON]->(parent)
            """, parent=parent_name, child=concept_name)
        
        # 递归处理子节点
        if "children" in node:
            for child in node["children"]:
                self._create_concept_node(session, child, concept_name)
    
    def _init_learning_progress(self, knowledge_tree: Dict, user_id: str):
        """初始化学习进度记录"""
        cursor = self.sqlite_conn.cursor()
        
        def traverse(node):
            concept_name = node.get("concept") or node.get("name")
            cursor.execute("""
                INSERT OR IGNORE INTO learning_progress 
                (concept_id, concept_name, mastery_score, weight, label)
                VALUES (random(), ?, 0, 0, 'New')
            """, (concept_name,))
            
            if "children" in node:
                for child in node["children"]:
                    traverse(child)
        
        traverse(knowledge_tree)
        self.sqlite_conn.commit()
    
    def _save_session_state(self, user_id: str, concept: str, stage: str, weaknesses: List):
        """保存会话状态用于断点续传"""
        cursor = self.sqlite_conn.cursor()
        cursor.execute("""
            INSERT INTO session_state (user_id, last_concept, last_stage, weaknesses)
            VALUES (?, ?, ?, ?)
        """, (user_id, concept, stage, json.dumps(weaknesses)))
        self.sqlite_conn.commit()
    
    def resume_session(self, user_id: str) -> Optional[Dict]:
        """恢复上次会话状态"""
        cursor = self.sqlite_conn.cursor()
        cursor.execute("""
            SELECT last_concept, last_stage, weaknesses, timestamp
            FROM session_state
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (user_id,))
        
        row = cursor.fetchone()
        if row:
            return {
                "concept": row[0],
                "stage": row[1],
                "weaknesses": json.loads(row[2]) if row[2] else [],
                "timestamp": row[3]
            }
        return None
    
    def close(self):
        """关闭连接"""
        self.neo4j_driver.close()
        self.sqlite_conn.close()


# ============ OpenClaw Skill 入口 ============

async def run_skill(input_data: Dict) -> Dict:
    """
    OpenClaw Skill 入口函数
    
    Args:
        input_data: {
            "action": "ingest" | "resume" | "import",
            "concept": str (optional),
            "content": str (optional),
            "user_id": str (optional),
            "file_path": str (optional)
        }
    
    Returns:
        处理结果
    """
    from neo4j import GraphDatabase
    
    # 从配置加载（实际使用时从 config.yaml 读取）
    neo4j_uri = "bolt://localhost:7687"
    neo4j_user = "neo4j"
    neo4j_password = "password"
    
    ingest = StudyIngest(neo4j_uri, neo4j_user, neo4j_password)
    
    try:
        action = input_data.get("action", "ingest")
        user_id = input_data.get("user_id", "default")
        
        if action == "ingest":
            concept = input_data.get("concept")
            content = input_data.get("content", "")
            if not concept:
                return {"status": "error", "message": "缺少 concept 参数"}
            
            result = await ingest.ingest_concept(concept, content, user_id)
            return result
            
        elif action == "resume":
            state = ingest.resume_session(user_id)
            if state:
                return {
                    "status": "success",
                    "message": f"上次学到 {state['concept']} 的 {state['stage']} 阶段",
                    "state": state
                }
            else:
                return {"status": "info", "message": "没有找到历史学习记录"}
                
        elif action == "import":
            file_path = input_data.get("file_path")
            if not file_path:
                return {"status": "error", "message": "缺少 file_path 参数"}
            
            # 读取文件内容
            content = Path(file_path).read_text()
            # TODO: 从内容中提取概念
            return {"status": "info", "message": "文件导入功能开发中"}
        
        else:
            return {"status": "error", "message": f"未知 action: {action}"}
    
    finally:
        ingest.close()


if __name__ == "__main__":
    # 本地测试
    import asyncio
    
    test_input = {
        "action": "ingest",
        "concept": "Transformer",
        "content": "今天学了 Transformer，它依赖自注意力机制",
        "user_id": "test_user"
    }
    
    result = asyncio.run(run_skill(test_input))
    print(json.dumps(result, indent=2, ensure_ascii=False))
