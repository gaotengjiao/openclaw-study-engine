import json
import re
from sqlalchemy.orm import Session
from app.core.config import settings
from .llm.adapters import DifyAdapter


class MasteryService:
    def __init__(self, db: Session):
        self.db = db
        cfg = settings.get("llm", {}).get("settings", {})
        self.adapter = DifyAdapter(cfg.get("api_key"), cfg.get("base_url", "http://127.0.0.1/v1"))

    async def evaluate_feynman(self, progress, user_content: str):
        prompt = f"你是一个费曼学习法专家。请评估用户对概念 {progress.concept_name} 的理解：{user_content}。请按此格式返回：SCORE:分数(0-100) FEEDBACK:评价"
        try:
            response = await self.adapter.generate_tree(
                prompt,
                "",
                concept=progress.concept_name,
                subject=progress.subject
            )

            score_match = re.search(r"SCORE:\s*(\d+)", response)
            feedback_match = re.search(r"FEEDBACK:\s*(.*)", response, re.DOTALL)

            score = int(score_match.group(1)) if score_match else 60
            feedback = feedback_match.group(1).strip() if feedback_match else response

            return {"score": score, "feedback": feedback}
        except Exception as e:
            print(f"⚠️ [Mastery Error] {e}")
            return {"score": 0, "feedback": "评分服务暂时离线"}