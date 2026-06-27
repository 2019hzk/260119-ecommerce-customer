from itertools import chain
from typing import Any

from jinja2 import Template
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from atguigu.domain.messages import BotMessage
from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult
from atguigu.infrastructure.llm_client import llm_client
from atguigu.history.builder import ChatHistoryBuilder


class ActionResponse(Action):
    name = "action_response"

    async def run(self,
                  state: DialogueState,
                  action_args: dict[str, Any]) -> ActionResult:
        """
        生成回复：回复的模版内容 （action_args：{"text":"{{name}}...."}）
        :param state:
        :param action_args:
        :return:
        """
        action_res_mode = action_args.get('mode', 'static')

        if action_res_mode == "static":
            text = action_args['text']
            render_text = self._render_text(text, state)
            return ActionResult(messages=[BotMessage(text=render_text)])
        elif action_res_mode == "rephrase":
            text = action_args['text']
            prompt_text = action_args['prompt']
            render_text = self._render_text(text, state)
            rewritten = await self._call_llm(state, prompt_text, render_text)
            return ActionResult(messages=[BotMessage(text=rewritten)])
        else:
            prompt_text = action_args['prompt']
            rewritten = await self._call_llm(state, prompt_text)
            return ActionResult(messages=[BotMessage(text=rewritten)])

    def _render_text(self, text: str,
                     state: DialogueState) -> str:
        """
        占位符中可能有变量:slots(业务流程) context(系统流程)
        :param text:
        :param state:
        :return:
        """

        template = Template(text)

        return template.render(slots=state.active_task.slots if state.active_task else {},
                               context=state.active_system_task)  # StartedSystemContext(started_flow_name="order_status_query")

    async def _call_llm(self,
                        state: DialogueState,
                        prompt_text: str,
                        render_text: str="") -> str:

        prompt_template = PromptTemplate.from_template(prompt_text)

        chain = prompt_template | llm_client | StrOutputParser()

        rewritten = await  chain.ainvoke({
            "history": ChatHistoryBuilder.build(state.current_session().turns[-10:]),
            "user_message": ChatHistoryBuilder.process_user_message(state.pending_turn.user_message),
            "current_response": render_text
        })

        return rewritten
