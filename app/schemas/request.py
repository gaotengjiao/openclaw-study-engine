from pydantic import BaseModel, Field
from typing import Optional

class IngestRequest(BaseModel):
    # 使用 Field 可以增加额外的约束和说明，类似 Java 的注解
    user_id: str = Field(..., example="adam_01", description="用户唯一标识")
    subject: str = Field(..., example="AI算法", description="学科类别")
    concept: str = Field(..., example="Transformer", description="要学习的概念名称")
    content: Optional[str] = Field(None, description="用户提供的初始笔记或内容")

    # 还可以自定义复杂的校验逻辑
    # 比如：确保学科不能为空字符串