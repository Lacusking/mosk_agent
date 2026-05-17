"""
通用类型与枚举定义

提供跨模块复用的基础类型。
"""

from enum import IntEnum
from enum import StrEnum


class Environment(StrEnum):
    """运行环境枚举。"""

    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"


class TaskStatus(StrEnum):
    """任务状态枚举。"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepType(StrEnum):
    """Step 类型枚举。"""

    MODEL = "model"
    TOOL = "tool"
    AGENT = "agent"
    WORKFLOW = "workflow"
    HUMAN = "human"
    SYSTEM = "system"


class RiskLevel(IntEnum):
    """风险等级枚举。"""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
