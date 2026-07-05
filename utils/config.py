"""
TwinOps AI - Configuration
============================
Loads and validates application configuration from environment variables.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from loguru import logger


@dataclass
class Config:
    """Application configuration."""
    google_api_key: str = ""
    app_env: str = "development"
    log_level: str = "INFO"
    agent_model: str = "gemini-2.0-flash"
    max_agent_iterations: int = 10
    agent_timeout_seconds: int = 120

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def has_api_key(self) -> bool:
        return bool(self.google_api_key and self.google_api_key != "your_gemini_api_key_here")


def load_config(env_file: Optional[str] = None) -> Config:
    """
    Load configuration from .env file and environment variables.
    Environment variables take precedence over .env file.
    """
    # Look for .env in project root
    if env_file:
        load_dotenv(env_file)
    else:
        # Walk up to find .env
        current = Path(__file__).parent
        for _ in range(4):
            env_path = current / ".env"
            if env_path.exists():
                load_dotenv(env_path)
                break
            current = current.parent

    config = Config(
        google_api_key=os.getenv("GOOGLE_API_KEY", ""),
        app_env=os.getenv("APP_ENV", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        agent_model=os.getenv("AGENT_MODEL", "gemini-2.0-flash"),
        max_agent_iterations=int(os.getenv("MAX_AGENT_ITERATIONS", "10")),
        agent_timeout_seconds=int(os.getenv("AGENT_TIMEOUT_SECONDS", "120")),
    )

    if not config.has_api_key:
        logger.warning(
            "GOOGLE_API_KEY not set or is placeholder. "
            "Agents will run in MOCK mode. "
            "Set GOOGLE_API_KEY in .env to enable Gemini AI."
        )

    return config
