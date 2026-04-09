import yaml
import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    config_data: dict = {}

    def __init__(self, **values):
        super().__init__(**values)
        # 定位项目根目录的 config.yaml
        current_dir = Path(__file__).resolve().parent
        config_path = current_dir.parent.parent / "config.yaml"

        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config_data = yaml.safe_load(f) or {}
            print(f"✅ [Config] 成功加载配置文件: {config_path}")
        else:
            print(f"❌ [Config] 找不到配置文件: {config_path}")

    def get(self, key: str, default=None):
        """模拟 dict.get 方法支持层级读取"""
        return self.config_data.get(key, default) or {}


settings = Settings()