"""Task Pydantic model - mirrors Claude Code's scheduled_tasks.json format."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class Task(BaseModel):
    """定时任务。镜像 Claude Code 的 JSON 字段,并扩展 MZC 自己的字段。"""
    id: str = Field(..., description="任务唯一 ID,由 Claude Code 分配")
    name: str = Field(..., description="任务显示名")
    prompt: str = Field(..., description="任务执行的 prompt 文本")
    schedule: str = Field(..., description="cron 表达式,例如 '0 9 * * *'")
    enabled: bool = Field(..., description="是否启用")
    created_at: datetime = Field(..., description="创建时间 (ISO 8601)")
    last_run: datetime | None = Field(default=None, description="上次运行时间")
    last_status: Literal["success", "failed", "timeout", "running", "never"] = Field(
        default="never", description="上次运行状态"
    )

    # MZC 扩展字段(不在 Claude Code JSON 里,在 SQLite 镜像中)
    created_by: str | None = Field(default=None, description="创建者标识")
    tags: list[str] = Field(default_factory=list, description="任务标签")
    next_run_at: datetime | None = Field(default=None, description="下次计划运行时间")
    synced_at: datetime | None = Field(default=None, description="从 JSON 同步到 SQLite 的时间")

    @field_validator("tags", mode="before")
    @classmethod
    def parse_tags(cls, v):
        if isinstance(v, str):
            import json
            return json.loads(v) if v else []
        return v

    def to_json_dict(self) -> dict:
        """Serialize for scheduled_tasks.json (only CC fields)."""
        return {
            "id": self.id,
            "name": self.name,
            "prompt": self.prompt,
            "schedule": self.schedule,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_status": self.last_status,
        }