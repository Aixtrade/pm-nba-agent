"""Loguru 日志配置"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional

from loguru import logger

_DEFAULT_LOG_DIR = "logs"
_FILE_FORMAT = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message}"
_STDOUT_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level}</level> | {message}"


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

    # stdout handler
    logger.add(
        sys.stdout,
        level=log_level,
        enqueue=True,
        backtrace=False,
        diagnose=False,
        colorize=True,
        format=_STDOUT_FORMAT,
    )

    # 文件持久化
    log_dir = Path(os.getenv("LOG_DIR", _DEFAULT_LOG_DIR))
    log_dir.mkdir(parents=True, exist_ok=True)

    _common_file_opts = dict(
        enqueue=True,
        backtrace=False,
        diagnose=False,
        colorize=False,
        format=_FILE_FORMAT,
        rotation="00:00",
        retention="30 days",
        compression="gz",
        encoding="utf-8",
    )

    # 全量日志
    logger.add(log_dir / "{time:YYYY-MM-DD}.log", level=log_level, **_common_file_opts)

    # 错误日志（ERROR + CRITICAL）
    logger.add(log_dir / "{time:YYYY-MM-DD}_error.log", level="ERROR", **_common_file_opts)

    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        target_logger = logging.getLogger(name)
        target_logger.handlers = [_InterceptHandler()]
        target_logger.propagate = False
