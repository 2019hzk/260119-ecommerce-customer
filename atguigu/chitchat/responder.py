from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from atguigu.domain.messages import BotMessage
from atguigu.domain.state import DialogueState
from atguigu.history.builder import ChatHistoryBuilder
from atguigu.prompts.loader import load_prompt_template
from atguigu.infrastructure.llm_client import llm_client


class ChitChatResponder:

    async def respond(self, state: DialogueState) -> list[BotMessage]:
        user_message = ChatHistoryBuilder.process_user_message(state.pending_turn.user_message)
        history = ChatHistoryBuilder.build(state.current_session().turns[-10:])

        prompt_text = load_prompt_template("chitchat_respond")
        prompt = PromptTemplate.from_template(prompt_text, template_format="jinja2")
        chain = prompt | llm_client | StrOutputParser()
        response = await chain.ainvoke({
            "user_message": user_message,
            "history": history,
        })
        return [BotMessage(text=response)]
