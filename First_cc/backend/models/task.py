"""Task Pydantic model - mirrors Claude Code's scheduled_tasks.json format."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class Task(BaseModel):
    """A scheduled task. Matches Claude Code's JSON schema."""
    id: str
    name: str
    prompt: str
    schedule: str  # cron expression
    enabled: bool = True
    created_at: datetime
    last_run: datetime | None = None
    last_status: Literal["success", "failed", "timeout", "running", "never"] = "never"

    # MZC extensions (not in Claude Code's JSON, but in our SQLite mirror)
    created_by: str | None = None
    tags: list[str] = Field(default_factory=list)
    next_run_at: datetime | None = None
    synced_at: datetime | None = None

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