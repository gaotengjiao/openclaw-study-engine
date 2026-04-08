import uvicorn
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi_amis_admin.admin.site import AdminSite
from fastapi_amis_admin.admin import admin
from fastapi_amis_admin.admin.settings import Settings

from app.db import models
from app.db.database import engine
from app.db.models import LearningProgress
from app.api.v1 import ingest

# 0. 路径定位
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "app" / "static"

# 1. 创建主 App
app = FastAPI(title="StudyEngine API")

# 2. 配置 AdminSite
site = AdminSite(
    settings=Settings(
        database_url_default='sqlite:///./study_engine.db',
        site_title="StudyEngine 管理后台",
    )
)

# 3. 注册 ModelAdmin
class LearningProgressAdmin(admin.ModelAdmin):
    model = LearningProgress
    page_schema = "学习进度中心"
    list_display = [LearningProgress.id, LearningProgress.concept_name, LearningProgress.weight]

site.register_admin(LearningProgressAdmin)

# ---------------------------------------------------------
# 【核心修正】：必须把 app 传给 mount_app 方法
# ---------------------------------------------------------
site.mount_app(app)

# 4. 注册业务路由
app.include_router(ingest.router, prefix="/api/v1/ingest", tags=["Ingest"])

# 5. 挂载静态文件
if not STATIC_DIR.exists():
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def read_index():
    index_path = STATIC_DIR / "index.html"
    return FileResponse(str(index_path)) if index_path.exists() else {"msg": "System Up"}


if __name__ == "__main__":
    # 【核心修正】：SQLModel 项目使用 SQLModel.metadata 而不是 models.Base
    from sqlmodel import SQLModel

    print(f"[Database] 正在初始化数据库表... 路径: {BASE_DIR}/study_engine.db")

    # 这行代码相当于 Hibernate 的 hbm2ddl.auto=update
    # 它会扫描所有继承了 SQLModel(table=True) 的类并创建表
    SQLModel.metadata.create_all(bind=engine)

    uvicorn.run(app, host="127.0.0.1", port=8000)