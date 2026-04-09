from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.request import IngestRequest
from app.services.ingest_service import IngestService

router = APIRouter()

@router.post("/")  # 修正：移除多余的 /ingest 层级
async def ingest_content(request: IngestRequest, db: Session = Depends(get_db)):
    """
    接收用户学习内容并触发 AI 审计流程
    """
    service = IngestService(db)
    try:
        result = await service.execute_full_ingest(request)
        return result
    except Exception as e:
        # Java 风格的全局异常捕获反馈
        raise HTTPException(status_code=500, detail=f"Service Error: {str(e)}")