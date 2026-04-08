from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Column, DateTime


class LearningProgress(SQLModel, table=True):
    __tablename__ = "learning_progress"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    subject: str = Field(index=True)
    concept_name: str = Field(index=True)

    # 权重：数值越大，越需要复习
    weight: int = Field(default=10)

    # 状态：New, Reviewing, Mastered, Struggling
    status: str = Field(default="New")

    # ---------------------------------------------------------
    # 【核心修正点】：不要同时使用 default 和 default_factory
    # 直接使用 datetime.now (不带括号) 作为默认值函数
    # ---------------------------------------------------------
    next_review_time: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime, nullable=False)
    )

    # 连续正确次数
    mastery_count: int = Field(default=0)

    # 最后一次更新时间
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime, onupdate=datetime.now)
    )