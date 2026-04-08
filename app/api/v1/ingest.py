from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.request import IngestRequest
from app.services.ingest_service import IngestService

router = APIRouter()

@router.post("/learn")
async def learn_concept(request: IngestRequest, db: Session = Depends(get_db)):
    """
    学习新概念接口
    """
    service = IngestService(db)
    try:
        result = await service.execute_full_ingest(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 注意：这里的路径是 "/"，因为在 main.py 中已经挂载了 "/api/v1/ingest"
@router.post("/")
async def ingest_content(request: IngestRequest, db: Session = Depends(get_db)):
    service = IngestService(db)
    return await service.execute_full_ingest(request)