import httpx
import json
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.db.models import LearningProgress


class MasteryService:
    def __init__(self, db: Session):
        self.db = db
        # 建议配置化：后期移入 app.core.config
        self.api_key = "app-xxxxxxxxxxxx"  # 填入你 Dify 应用的 API Key
        self.base_url = "http://你的服务器IP/v1"  # 如果是本机，确保容器间网络通畅

    async def evaluate_feynman(self, progress: LearningProgress, user_content: str):
        """
        调用 Dify API 对用户的费曼解释进行语义审计
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # 构建发送给 Dify 的参数
        # 这里的 inputs 对应你在 Dify 工作流中定义的变量
        payload = {
            "inputs": {
                "concept": progress.concept_name,
                "subject": progress.subject
            },
            "query": user_content,
            "response_mode": "blocking",
            "user": progress.user_id
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/completion-messages",
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )
                response.raise_for_status()
                data = response.json()

            # 解析 Dify 的返回内容
            # 假设你在 Dify 输出中返回了类似 "SCORE:85; FEEDBACK:解释得很好"
            full_answer = data.get("answer", "")

            # 解析逻辑（建议在 Dify 中直接输出 JSON 格式字符串方便解析）
            score, feedback = self._parse_ai_result(full_answer)

            # 更新权重算法
            self._update_learning_weight(progress, score)

            return {
                "score": score,
                "feedback": feedback,
                "new_weight": progress.weight,
                "status": progress.status
            }

        except Exception as e:
            print(f"[MasteryError] 审计失败: {str(e)}")
            return {"error": "AI 审计服务暂时离线，请稍后再试"}

    def _parse_ai_result(self, ai_text: str):
        """
        解析 AI 返回的文本（建议后期让 Dify 直接出 JSON）
        """
        # 简单示例逻辑：如果 AI 返回包含分数
        try:
            # 这里可以用正则提取数字，暂做模拟
            if "80" in ai_text: return 85, ai_text
            return 60, ai_text
        except:
            return 50, "无法解析评分"

    def _update_learning_weight(self, progress: LearningProgress, score: int):
        """
        费曼学习法权重调整算法
        """
        if score >= 80:
            # 掌握良好：减小权重（降低复习频率）
            progress.weight = max(0, progress.weight - 5)
            progress.status = "Mastered"
            # 自动计算下一次复习时间（比如 3 天后）
            progress.next_review_time = datetime.now() + timedelta(days=3)
        else:
            # 掌握欠缺：增加权重（提高复习频率）
            progress.weight = min(100, progress.weight + 10)
            progress.status = "Struggling"
            progress.next_review_time = datetime.now() + timedelta(hours=12)

        self.db.commit()