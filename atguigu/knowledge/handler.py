from atguigu.domain.messages import BotMessage
from atguigu.domain.state import DialogueState
from atguigu.knowledge.intents import KnowledgeIntent
from atguigu.knowledge.providers.registry import KnowledgeProviderRegistry
from atguigu.knowledge.responder import KnowledgeResponder


class KnowledgeHandler:

    def __init__(self,
                 knowledge_intents: dict[str, KnowledgeIntent],
                 knowledge_register: KnowledgeProviderRegistry,
                 knowledge_responder: KnowledgeResponder
                 ):
        self.knowledge_intents = knowledge_intents
        self.knowledge_register = knowledge_register
        self.knowledge_responder = knowledge_responder

    async def hand(self,
                   state: DialogueState,
                   intents: list[str]) -> list[BotMessage]:
        """

        :param state:
        :param intents:  LLM输出的["product_info","order_info"]
        :return:
        """

        # 1. 根据intents知识意图ID 查询提供者ID
        provider_ids = self._fetch_provider_ids_by_intents(intents)

        # 2. 根据提供者ID 查询
        final_chunks = []
        for provider_id in provider_ids:
            provider = self.knowledge_register.get(provider_id)
            knowledge_chunks = await provider.retrieve(state)
            final_chunks.extend(knowledge_chunks)

        # 3. 调用LLM 得到响应结果
        return await self.knowledge_responder.respond(user_message=state.pending_turn.user_message,
                                                      recent_turns=state.current_session().turns[-10:],
                                                      chunks=final_chunks
                                                      )

    def _fetch_provider_ids_by_intents(self, intents: list[str]) -> list[str]:
        final_provider_ids = []
        for intent_id in intents:
            knowledge_intent = self.knowledge_intents[intent_id]
            final_provider_ids.extend(knowledge_intent.provider_ids)

        return list(set(final_provider_ids))  # 去重
