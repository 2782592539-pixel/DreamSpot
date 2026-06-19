"""Configuration loaded from .env file."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MZC_",
        case_sensitive=False,
        extra="ignore",
    )

    # Service
    host: str = "127.0.0.1"
    port: int = 8765
    log_level: str = "INFO"

    # Paths
    claude_home: str = r"C:\Users\27825"
    db_path: str = r"C:\Users\27825\Desktop\First_cc\data\mzc.db"
    log_path: str = r"C:\Users\27825\Desktop\First_cc\logs\mzc.log"

    # Claude Code
    claude_cli: str = "claude"

    # Feishu
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_webhook_url: str = ""  # 飞书自定义机器人 webhook URL (e.g. https://open.feishu.cn/hook/...)
    feishu_webhook_verify_token: str = ""
    feishu_webhook_encrypt_key: str = ""

    # Cloudflare Access
    cf_access_aud: str = ""
    cf_access_team_domain: str = ""

    @property
    def scheduled_tasks_path(self) -> Path:
        return Path(self.claude_home) / ".claude" / "scheduled_tasks.json"

    @property
    def projects_dir(self) -> Path:
        return Path(self.claude_home) / ".claude" / "projects"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
