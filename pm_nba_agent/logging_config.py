"""Loguru 日志配置"""

from __future__ import annotations

import logging
import os
import sys
from typing import Optional

from loguru import logger


class _InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def configure_logging(level: Optional[str] = None) -> None:
    """配置 Loguru 并接管标准 logging。"""
    log_level = level or os.getenv("LOG_LEVEL", "INFO")

    logger.remove()
    logger.add(
        sys.stdout,
        level=log_level,
        enqueue=True,
        backtrace=False,
        diagnose=False,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level}</level> | {message}",
    )

    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        target_logger = logging.getLogger(name)
        target_logger.handlers = [_InterceptHandler()]
        target_logger.propagate = False
