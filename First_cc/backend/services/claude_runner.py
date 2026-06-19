"""Wrapper around `claude -p` subprocess for one-shot task execution."""
import logging
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from backend.config import get_settings

logger = logging.getLogger(__name__)

# 10 minutes per spec §6.4
DEFAULT_TIMEOUT_SEC = 600


@dataclass
class ClaudeRunResult:
    exit_code: int
    output: str
    error: str
    started_at: datetime
    finished_at: datetime
    duration_sec: int

    @property
    def status(self) -> str:
        if self.exit_code == 0:
            return "success"
        return "failed"


class ClaudeRunner:
    def __init__(self, claude_cli: str | None = None, timeout_sec: int = DEFAULT_TIMEOUT_SEC):
        self.claude_cli = claude_cli or get_settings().claude_cli
        self.timeout_sec = timeout_sec

    def run(self, prompt: str, working_dir: Path | None = None) -> ClaudeRunResult:
        """Run `claude -p "<prompt>"` and return result."""
        started = datetime.now()
        cmd = [self.claude_cli, "-p", prompt, "--output-format", "json"]
        logger.info(f"Running: {' '.join(cmd[:2])} <prompt len={len(prompt)}>")

        kwargs = {
            "capture_output": True,
            "text": True,
            "timeout": self.timeout_sec,
        }
        if working_dir:
            kwargs["cwd"] = str(working_dir)
        if sys.platform == "win32":
            # Suppress console window flash
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        try:
            proc = subprocess.run(cmd, **kwargs)
        except subprocess.TimeoutExpired as e:
            logger.error(f"Claude run timed out after {self.timeout_sec}s")
            raise TimeoutError(f"Claude run timed out after {self.timeout_sec}s") from e

        finished = datetime.now()
        return ClaudeRunResult(
            exit_code=proc.returncode,
            output=proc.stdout or "",
            error=proc.stderr or "",
            started_at=started,
            finished_at=finished,
            duration_sec=int((finished - started).total_seconds()),
        )
