from atguigu.domain.messages import ProcessResult, UserMessage, ChatHistoryMessage
from atguigu.repository.dialogue_repository import DialogueRepository
from atguigu.domain.state import DialogueState
from atguigu.engine.dialogue_engine import DialogueEngine
from atguigu.history.builder import ChatHistoryBuilder


class DialogueService:
    """
    处理对话的服务类
    """

    def __init__(self,
                 repository: DialogueRepository,
                 engine: DialogueEngine):
        print(f"repository:{id(repository)}")
        print(f"engine:{id(engine)}")

        self.repository = repository
        self.engine = engine

    async def hand_dialogue(self, user_message: UserMessage) -> ProcessResult:
        """
        IO：【读写数据库：repository】/计算[engine]
        :param user_message:
        :return:
        """

        # 1. 从数据库中读取之前的DialogueState
        dialogue_state: DialogueState = await self.repository.load_dialogue(user_message.sender_id)

        # 2. 引擎层使用(修改DialogueState的状态)
        process_result: ProcessResult = await self.engine.hand_message(user_message, dialogue_state)

        # 3. 将修改后的修改DialogueState的状态 存储到数据库中
        await  self.repository.save_dialogue(dialogue_state)

        return process_result

    async def load_chat_history(self, sender_id: str) -> list[ChatHistoryMessage]:
        # 1. 根据sender_id查询对话状态
        dialogue_state = await self.repository.load_dialogue(sender_id)

        # 2. 获取sessions
        user_sessions = dialogue_state.sessions

        result = []

        # 3. 遍历user_sessions列表
        for session in user_sessions:

            for turn in session.turns:

                # 3.1 处理用户角色的历史消息
                user_message = turn.user_message
                user_history_message = ChatHistoryBuilder.build_chat_history(session_id=session.session_id,
                                                                             role="user",
                                                                             text=user_message.text,
                                                                             object=user_message.object)
                result.append(user_history_message)

                # 3.2 处理机器人角色的历史消息
                bot_messages = turn.bot_messages

                for bot_message in bot_messages:
                    bot_history_message = ChatHistoryBuilder.build_chat_history(
                        session_id=session.session_id,
                        role="bot",
                        text=bot_message.text,
                        object=bot_message.object
                    )
                    result.append(bot_history_message)
        return result
