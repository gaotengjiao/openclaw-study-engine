from neo4j import AsyncGraphDatabase
from typing import Dict, Optional
import datetime


class GraphService:
    def __init__(self, uri: str, user: str, password: str):
        # 使用异步驱动以匹配 FastAPI 的异步特性
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    async def close(self):
        await self.driver.close()

    async def upsert_concept_graph(self, user_id: str, subject: str, knowledge_tree: Dict):
        """
        入口方法：将知识树存入 Neo4j
        """
        user_label = f"User_{user_id}"  # 动态生成用户隔离标签

        async with self.driver.session() as session:
            # 使用异步事务执行递归写入
            await session.execute_write(
                self._recursive_upsert,
                user_label,
                subject,
                knowledge_tree,
                None
            )

    async def _recursive_upsert(self, tx, user_label: str, subject: str, node: Dict, parent_name: Optional[str]):
        """
        递归写入节点和关系
        """
        concept_name = node.get("name")
        if not concept_name:
            return

        # 1. 创建/更新概念节点 (带有用户标签和学科属性)
        # 使用 MERGE 保证幂等性
        query = f"""
        MERGE (c:Concept:{user_label} {{name: $name, subject: $subject}})
        ON CREATE SET c.created_at = datetime(), c.version = 1
        ON MATCH SET c.updated_at = datetime(), c.version = c.version + 1
        """
        await tx.run(query, name=concept_name, subject=subject)

        # 2. 如果存在父节点，建立 DEPENDS_ON 关系
        if parent_name:
            rel_query = f"""
            MATCH (p:Concept:{user_label} {{name: $p_name, subject: $subject}})
            MATCH (c:Concept:{user_label} {{name: $c_name, subject: $subject}})
            MERGE (c)-[:DEPENDS_ON]->(p)
            """
            await tx.run(rel_query, p_name=parent_name, c_name=concept_name, subject=subject)

        # 3. 处理子节点
        children = node.get("children", [])
        for child in children:
            await self._recursive_upsert(tx, user_label, subject, child, concept_name)