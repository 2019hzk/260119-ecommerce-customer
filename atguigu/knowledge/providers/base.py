from abc import ABC, abstractmethod
from dataclasses import dataclass

from atguigu.domain.state import DialogueState

@dataclass
class KnowledgeChunk:
    content: str   # 检索到的内容


class KnowledgeProvider(ABC):
    provider_id = ""

    @abstractmethod
    async def retrieve(
            self,
            state: DialogueState,
    ) -> list[KnowledgeChunk]:
        pass



