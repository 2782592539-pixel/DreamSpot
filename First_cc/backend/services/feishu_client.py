"""Feishu webhook client - sends interactive cards."""
import logging
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)


@dataclass
class FeishuCard:
    header: dict = field(default_factory=dict)
    body: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "msg_type": "interactive",
            "card": {
                "header": self.header,
                "elements": self.body.get("elements", []),
            },
        }


class FeishuClient:
    def __init__(self, webhook_url: str | None = None, timeout_sec: float = 10.0):
        # Resolve webhook URL: explicit arg > MZC_FEISHU_WEBHOOK_URL env var > empty
        if webhook_url is None:
            from backend.config import get_settings
            webhook_url = get_settings().feishu_webhook_url or None
        self.webhook_url = webhook_url  # may be None — send() will skip in that case
        self.timeout_sec = timeout_sec

    def build_task_card(
        self,
        task_name: str,
        status: str,
        output_summary: str,
        task_id: str,
        run_id: int,
    ) -> FeishuCard:
        emoji = "✅" if status == "success" else "❌"
        color = "green" if status == "success" else "red"
        header = {
            "title": {"tag": "plain_text", "content": f"{emoji} {task_name}"},
            "template": color,
        }
        body = {
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "plain_text",
                        "content": output_summary[:500] if output_summary else "(无输出)",
                    },
                },
                {"tag": "hr"},
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "查看详情"},
                            "type": "primary",
                            "value": {
                                "action": "view_detail",
                                "task_id": task_id,
                                "run_id": run_id,
                            },
                        },
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "再次执行"},
                            "type": "default",
                            "value": {
                                "action": "rerun",
                                "task_id": task_id,
                            },
                        },
                    ],
                },
            ]
        }
        return FeishuCard(header=header, body=body)

    async def send(self, card: FeishuCard) -> bool:
        if not self.webhook_url:
            return False
        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                resp = await client.post(self.webhook_url, json=card.to_dict())
            if resp.status_code == 200 and resp.json().get("code") == 0:
                return True
            if resp.status_code == 429:
                logger.warning("Feishu rate limited (429)")
                return False
            logger.error(f"Feishu send failed: {resp.status_code} {resp.text[:200]}")
            return False
        except httpx.HTTPError:
            logger.exception("Feishu send network error")
            return False
