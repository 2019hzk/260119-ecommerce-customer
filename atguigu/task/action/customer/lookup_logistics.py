from typing import Any

from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult
from atguigu.task.action.customer.shared import fetch_logistics


class LookupLogisticsAction(Action):
    name = "action_lookup_logistics"

    async def run(self, state: DialogueState, action_args: dict[str, Any]) -> ActionResult:
        """
        根据订单ID 查询订单的物流信息
        :param state:
        :param action_args:
        :return:
        """
        order_id = state.active_task.slots.get('order_number')

        result: dict[str, Any] = await fetch_logistics(order_id=order_id)

        if result is None:
            return ActionResult(slot_updates={
                "tracking_number": "未知",
                "logistics_company": "未知",
                "logistics_status": "暂时无法查到物流信息，请稍后再试。",

            })
        return ActionResult(
            slot_updates={
                "tracking_number": result.get("tracking_number") or "未知",
                "logistics_company": result.get("logistics_company") or "未知",
                "logistics_status": result.get("status_desc") or result.get("status") or "未知",
            }
        )

