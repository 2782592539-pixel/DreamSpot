"""Tests for Feishu client - sends interactive cards via webhook URL."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from backend.services.feishu_client import FeishuClient, FeishuCard


def test_build_task_card():
    client = FeishuClient(webhook_url="https://example.com/wh")
    card = client.build_task_card(
        task_name="Daily report",
        status="success",
        output_summary="Report generated successfully",
        task_id="t_1",
        run_id=42,
    )
    assert card.header["title"]["content"] == "✅ Daily report"
    assert "Report generated" in card.body["elements"][0]["text"]["content"]


def test_build_task_card_failure():
    client = FeishuClient(webhook_url="https://example.com/wh")
    card = client.build_task_card(
        task_name="Backup",
        status="failed",
        output_summary="Permission denied",
        task_id="t_2",
        run_id=43,
    )
    assert "❌" in card.header["title"]["content"]


@pytest.mark.asyncio
async def test_send_card_success():
    client = FeishuClient(webhook_url="https://example.com/wh")
    card = client.build_task_card(
        task_name="x", status="success", output_summary="ok",
        task_id="t_x", run_id=1,
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"code": 0, "msg": "ok"}
        mock_post.return_value = mock_resp
        result = await client.send(card)
    assert result is True


@pytest.mark.asyncio
async def test_send_card_rate_limited_returns_false():
    client = FeishuClient(webhook_url="https://example.com/wh")
    card = client.build_task_card(
        task_name="x", status="success", output_summary="ok",
        task_id="t_x", run_id=1,
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 429
        result = await client.send(card)
    assert result is False
