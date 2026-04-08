import yaml
import os
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from pathlib import Path

# 1. 定义子配置结构 (类似 Java 的嵌套 DTO)
class LLMSettings(BaseModel):
    provider: str
    api_key: str
    default_model: Optional[str] = "qwen-plus"
    base_url: Optional[str] = None
    temperature: float = 0.7

class Settings(BaseModel):
    # 根据你的 config.yaml 结构定义字段
    database: Dict[str, str]
    llm: Dict[str, Any]
    learning: Dict[str, Any]
    sensitivity: Dict[str, Any]

    @classmethod
    def load(cls):
        # 自动定位项目根目录下的 config.yaml
        # __file__ 是 app/core/config.py，parent.parent.parent 回到根目录
        base_dir = Path(__file__).resolve().parent.parent.parent
        config_path = base_dir / "config.yaml"

        if not config_path.exists():
            raise FileNotFoundError(f"未找到配置文件: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            # Pydantic V2 的实例化方式
            return cls(**data)

# 2. 单例模式导出配置对象
# 这样在其他模块 import settings 即可直接使用
try:
    settings = Settings.load()
    # 为了方便你后续用 settings.llm 访问字典，将其转化为普通字典（如果需要）
    # 或者直接作为 Pydantic 对象使用
    settings_dict = settings.model_dump()
except Exception as e:
    print(f"[Config Error] 配置加载失败: {e}")
    # 提供一个默认空配置或直接抛出异常阻止程序启动
    raise e