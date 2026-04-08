from abc import ABC, abstractmethod
from typing import Dict

class BaseLLMAdapter(ABC):
    @abstractmethod
    async def generate_tree(self, prompt: str, model_name: str) -> str:
        """所有适配器必须实现此方法以返回原始文本"""
        pass