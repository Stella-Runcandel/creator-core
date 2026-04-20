from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv

ENV_PATH = Path('.env')


def load_config() -> Dict[str, Optional[str]]:
    """Load configuration from .env into process env and return key values."""
    load_dotenv(override=False)
    return {
        'YOUTUBE_API_KEY': os.getenv('YOUTUBE_API_KEY'),
        'CHANNEL_ID': os.getenv('CHANNEL_ID'),
        'DB_PATH': os.getenv('DB_PATH', 'creator_core.db'),
        'REFRESH_VIDEO_LIMIT': os.getenv('REFRESH_VIDEO_LIMIT', '50'),
    }


def get_refresh_video_limit(cfg: Dict[str, Optional[str]]) -> int:
    raw_limit = cfg.get('REFRESH_VIDEO_LIMIT')
    try:
        limit = int(raw_limit or 50)
    except (TypeError, ValueError):
        limit = 50
    return max(1, limit)


def ensure_env_file_exists() -> None:
    if not ENV_PATH.exists():
        ENV_PATH.write_text('', encoding='utf-8')


def _read_env_lines() -> list[str]:
    if not ENV_PATH.exists():
        return []
    return ENV_PATH.read_text(encoding='utf-8').splitlines()


def save_env_value(key: str, value: str) -> None:
    """Save or update one key=value in .env."""
    ensure_env_file_exists()
    lines = _read_env_lines()

    updated = False
    new_lines: list[str] = []
    prefix = f'{key}='

    for line in lines:
        if line.startswith(prefix):
            new_lines.append(f'{key}={value}')
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(f'{key}={value}')

    ENV_PATH.write_text('\n'.join(new_lines) + '\n', encoding='utf-8')


def validate_fetch_config(cfg: Dict[str, Optional[str]]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not cfg.get('YOUTUBE_API_KEY'):
        errors.append('YOUTUBE_API_KEY is missing in .env')
    if not cfg.get('CHANNEL_ID'):
        errors.append('CHANNEL_ID is missing in .env (run: python main.py setup)')
    return (len(errors) == 0, errors)
