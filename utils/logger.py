"""
TwinOps AI - Logging Setup
============================
Configures Loguru for structured, leveled logging.
"""

import sys
from pathlib import Path
from typing import Optional
from loguru import logger


def setup_logger(log_level: str = "INFO", log_dir: Optional[str] = None) -> None:
    """
    Configure application-wide logging.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR)
        log_dir: Directory for log file output (optional)
    """
    # Remove default handler
    logger.remove()

    # Console output with color
    logger.add(
        sys.stdout,
        level=log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # File output (rotating)
    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_path / "twinops_{time:YYYY-MM-DD}.log",
            level="DEBUG",
            rotation="1 day",
            retention="7 days",
            compression="gz",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        )
