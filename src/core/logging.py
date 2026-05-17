"""
结构化日志系统

支持 JSON / 彩色控制台 / 文件输出，自动注入 request_id 与 trace_id。
"""

import json
import logging
import logging.handlers
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from src.core.context import request_id_ctx
from src.core.context import trace_id_ctx


class ColorCodes:
    """ANSI 颜色码常量。"""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_RED = "\033[91m"
    WHITE = "\033[37m"


class JSONFormatter(logging.Formatter):
    """JSON 格式化器，将日志记录转换为 JSON 格式。"""

    def __init__(
        self, include_extra: bool = True, indent: int | None = None, use_color: bool = False
    ):
        super().__init__()
        self.include_extra = include_extra
        self.indent = indent
        self.use_color = use_color
        self.level_colors = {
            "DEBUG": ColorCodes.BRIGHT_BLUE,
            "INFO": ColorCodes.BRIGHT_GREEN,
            "WARNING": ColorCodes.BRIGHT_YELLOW,
            "ERROR": ColorCodes.BRIGHT_RED,
            "CRITICAL": ColorCodes.BOLD + ColorCodes.BRIGHT_RED,
        }

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process": record.process,
            "thread": record.thread,
            "request_id": getattr(record, "request_id", "-"),
            "trace_id": getattr(record, "trace_id", "-"),
        }

        if record.exc_info and record.exc_info[0] is not None:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        if self.include_extra:
            skip_keys = {
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs", "message",
                "pathname", "process", "processName", "relativeCreated",
                "thread", "threadName", "exc_info", "exc_text", "stack_info",
                "taskName", "request_id", "trace_id",
            }
            extra_fields = {
                k: v for k, v in record.__dict__.items() if k not in skip_keys
            }
            if extra_fields:
                log_data["extra"] = extra_fields

        json_str = json.dumps(log_data, ensure_ascii=False, indent=self.indent, default=str)

        if self.use_color:
            color = self.level_colors.get(record.levelname, ColorCodes.WHITE)
            json_str = f"{color}{json_str}{ColorCodes.RESET}"

        return json_str


class ColoredStandardFormatter(logging.Formatter):
    """带颜色的标准格式化器，用于控制台输出。"""

    def __init__(self, fmt: str, use_color: bool = True):
        super().__init__(fmt=fmt)
        self.use_color = use_color
        self.level_colors = {
            "DEBUG": ColorCodes.BRIGHT_BLUE,
            "INFO": ColorCodes.BRIGHT_GREEN,
            "WARNING": ColorCodes.BRIGHT_YELLOW,
            "ERROR": ColorCodes.BRIGHT_RED,
            "CRITICAL": ColorCodes.BOLD + ColorCodes.BRIGHT_RED,
        }

    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "request_id"):
            record.request_id = "-"  # type: ignore[attr-defined]
        if not hasattr(record, "trace_id"):
            record.trace_id = "-"  # type: ignore[attr-defined]
        formatted = super().format(record)
        if self.use_color:
            color = self.level_colors.get(record.levelname, ColorCodes.WHITE)
            formatted = formatted.replace(
                record.levelname, f"{color}{record.levelname}{ColorCodes.RESET}", 1
            )
        return formatted


class StandardFormatter(logging.Formatter):
    """标准格式化器，用于文件输出。"""

    def __init__(self, fmt: str):
        super().__init__(fmt=fmt)

    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "request_id"):
            record.request_id = "-"  # type: ignore[attr-defined]
        if not hasattr(record, "trace_id"):
            record.trace_id = "-"  # type: ignore[attr-defined]
        return super().format(record)


class RequestContextFilter(logging.Filter):
    """为日志记录注入 request_id 与 trace_id 上下文。"""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id") or record.request_id == "-":  # type: ignore[attr-defined]
            record.request_id = request_id_ctx.get(None) or "-"  # type: ignore[attr-defined]
        if not hasattr(record, "trace_id") or record.trace_id == "-":  # type: ignore[attr-defined]
            record.trace_id = trace_id_ctx.get(None) or "-"  # type: ignore[attr-defined]
        return True


class LoggerConfig:
    """Logger 配置管理类。"""

    LEVEL_MAPPING = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    def __init__(
        self,
        name: str = "mosk_agent",
        level: str = "INFO",
        log_dir: str = "logs",
        log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s",
        console_json: bool = True,
        file_json: bool = True,
        json_indent: int | None = 2,
        console_color: bool = True,
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 5,
        enable_console: bool = True,
        enable_file: bool = True,
        exclude_logger_name: list[str] | None = None,
    ):
        self.name = name
        self.level = self.LEVEL_MAPPING.get(level.upper(), logging.INFO)
        self.log_dir = Path(log_dir)
        self.log_format = log_format
        self.console_json = console_json
        self.file_json = file_json
        self.json_indent = json_indent
        self.console_color = console_color
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.enable_console = enable_console
        self.enable_file = enable_file
        self.exclude_logger_name = exclude_logger_name or []

        if self.enable_file:
            self.log_dir.mkdir(parents=True, exist_ok=True)

        self._file_handlers: list[logging.Handler] = []
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger()
        logger.setLevel(self.level)
        logger.handlers.clear()
        logger.filters.clear()
        logger.addFilter(RequestContextFilter())
        logger.propagate = False

        if self.enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.level)
            if self.console_json:
                console_handler.setFormatter(
                    JSONFormatter(indent=self.json_indent, use_color=self.console_color)
                )
            else:
                console_handler.setFormatter(
                    ColoredStandardFormatter(fmt=self.log_format, use_color=self.console_color)
                )
            console_handler.addFilter(RequestContextFilter())
            logger.addHandler(console_handler)

        if self.enable_file:
            all_logs = logging.handlers.RotatingFileHandler(
                self.log_dir / f"{self.name}_all.log",
                maxBytes=self.max_bytes,
                backupCount=self.backup_count,
                encoding="utf-8",
            )
            all_logs.setLevel(self.level)
            all_logs.setFormatter(StandardFormatter(fmt=self.log_format))
            all_logs.addFilter(RequestContextFilter())
            logger.addHandler(all_logs)
            self._file_handlers.append(all_logs)

            error_handler = logging.handlers.RotatingFileHandler(
                self.log_dir / f"{self.name}_error.log",
                maxBytes=self.max_bytes,
                backupCount=self.backup_count,
                encoding="utf-8",
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(StandardFormatter(fmt=self.log_format))
            error_handler.addFilter(RequestContextFilter())
            logger.addHandler(error_handler)
            self._file_handlers.append(error_handler)

        # 排除指定 logger
        for name in self.exclude_logger_name:
            excluded = logging.getLogger(name)
            excluded.handlers.clear()
            excluded.propagate = False

        return logger


class LoggerManager:
    """Logger 单例管理器。"""

    _instance: logging.Logger | None = None
    _initialized: bool = False

    @classmethod
    def initialize(cls, **kwargs: Any) -> logging.Logger:
        """初始化单例 logger。"""
        config = LoggerConfig(**kwargs)
        cls._instance = config.logger
        cls._initialized = True
        return cls._instance

    @classmethod
    def get_instance(cls) -> logging.Logger:
        """获取 logger 实例，未初始化则使用默认配置。"""
        if cls._instance is None:
            cls.initialize()
        return cls._instance  # type: ignore[return-value]

    @classmethod
    def is_initialized(cls) -> bool:
        return cls._initialized

    @classmethod
    def reset(cls) -> None:
        if cls._instance:
            cls._instance.handlers.clear()
            cls._instance.filters.clear()
        cls._instance = None
        cls._initialized = False


def setup_logger(**kwargs: Any) -> logging.Logger:
    """初始化并返回全局 logger。"""
    return LoggerManager.initialize(**kwargs)


def get_logger() -> logging.Logger:
    """获取全局 logger 实例。"""
    return LoggerManager.get_instance()
