from sqlalchemy.orm import Session
from datetime import datetime
from app.db.models import LearningProgress
from app.schemas.request import IngestRequest
from .llm_service import LLMProcessor
from .mastery_service import MasteryService


class IngestService:
    def __init__(self, db: Session):
        self.db = db
        self.llm = LLMProcessor()
        self.mastery = MasteryService(db)

    async def execute_full_ingest(self, request: IngestRequest):
        """
        核心业务流：知识提取 -> 进度管理 -> 语义审计
        """

        # 1. 调用 LLM 生成知识结构树 (增加异常隔离)
        try:
            knowledge_tree = await self.llm.get_completed_tree(
                subject=request.subject,
                concept=request.concept,
                user_content=request.content
            )
        except Exception as e:
            print(f"⚠️ [LLM Error] 知识树生成失败: {e}")
            knowledge_tree = {"name": request.concept, "children": []}

        # 2. 查询或初始化用户进度
        progress = self.db.query(LearningProgress).filter_by(
            user_id=request.user_id,
            concept_name=request.concept
        ).first()

        if not progress:
            progress = LearningProgress(
                user_id=request.user_id,
                subject=request.subject,
                concept_name=request.concept,
                weight=10,
                status="New",
                next_review_time=datetime.now()
            )
            self.db.add(progress)
            self.db.flush()

        # 4. 执行费曼语义审计 (增加异常隔离)
        evaluation_result = None
        if request.content and len(request.content.strip()) > 5:
            try:
                evaluation_result = await self.mastery.evaluate_feynman(
                    progress=progress,
                    user_content=request.content
                )
            except Exception as e:
                print(f"⚠️ [Mastery Error] AI 审计失败: {e}")
                evaluation_result = {
                    "score": 0,
                    "feedback": "理解已保存，但 AI 导师目前不在线，请稍后再看评估。"
                }

        # 5. 显式提交事务
        try:
            self.db.commit()
            self.db.refresh(progress)
        except Exception as e:
            self.db.rollback()
            raise e

        # 6. 返回结果
        return {
            "concept": request.concept,
            "subject": request.subject,
            "knowledge_tree": knowledge_tree,
            "current_progress": {
                "weight": progress.weight,
                "status": progress.status,
                "next_review": progress.next_review_time.strftime("%Y-%m-%d %H:%M")
            },
            "evaluation": evaluation_result
        }