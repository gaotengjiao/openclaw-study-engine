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
        核心业务流：加入异常隔离机制
        """

        # 1. 知识提取 (增加 Try-Except 隔离)
        # 即使 AI 生成树失败，我们也给前端一个空的根节点，保证流程不中断
        try:
            knowledge_tree = await self.llm.get_completed_tree(
                subject=request.subject,
                concept=request.concept,
                user_content=request.content
            )
        except Exception as e:
            print(f"⚠️ [LLM Error] 生成知识树失败: {str(e)}")
            knowledge_tree = {"name": request.concept, "children": []}

        # 2. 进度查询
        progress = self.db.query(LearningProgress).filter_by(
            user_id=request.user_id,
            concept_name=request.concept
        ).first()

        # 3. 初始化/更新基础记录
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

        # 4. 执行费曼审计 (保持异常隔离)
        evaluation_result = None
        if request.content and len(request.content.strip()) > 5:
            try:
                evaluation_result = await self.mastery.evaluate_feynman(
                    progress=progress,
                    user_content=request.content
                )
            except Exception as e:
                # 降级处理：告知用户录入成功但审计延迟
                print(f"⚠️ [Mastery Error] AI 审计失败: {str(e)}")
                evaluation_result = {
                    "score": 0,
                    "feedback": "您的理解已录入，但 AI 导师暂时忙碌，稍后为您评估。",
                    "offline": True
                }

        # 5. 提交事务
        try:
            self.db.commit()
            self.db.refresh(progress)
        except Exception as e:
            self.db.rollback()
            raise e

        # 6. 返回聚合结果
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