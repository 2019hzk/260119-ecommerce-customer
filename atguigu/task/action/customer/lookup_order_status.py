from typing import Any

from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult
from atguigu.task.action.customer.shared import fetch_order, _build_order_summary
from atguigu.infrastructure import http_client


class LookupOrderStatusAction(Action):
    name = "action_lookup_order_status"

    async def run(self, state: DialogueState, action_args: dict[str, Any]) -> ActionResult:
        """
        从中台服务中查询物流状态接口
        :param state:
        :param action_args:
        :return:
        """
        order_number = state.active_task.slots.get("order_number")
        payload = await fetch_order(order_number)

        if payload is None:
            return ActionResult(slot_updates={
                "order_status": "未知",
                "order_summary": "暂时无法查到该订单信息，请稍后再试。",
            })

        return ActionResult(
            slot_updates={
                "order_status": payload.get("status_desc") or payload.get("status") or "未知",
                "order_summary": _build_order_summary(payload)
            }
        )

