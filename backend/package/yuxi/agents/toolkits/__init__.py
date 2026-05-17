# toolkits 包
# 触发各模块的 @tool 装饰器执行，自动注册工具
from importlib import import_module

from . import breeding

# 工具获取函数
from .registry import (
    ToolExtraMetadata,
    get_all_extra_metadata,
    get_all_tool_instances,
    get_extra_metadata,
    tool,
)

__all__ = [
    "get_extra_metadata",
    "get_all_extra_metadata",
    "get_all_tool_instances",
    "ToolExtraMetadata",
    "tool",
    # 触发各模块的 @tool 装饰器执行，自动注册工具
    "breeding",
    "get_common_kb_tools",
    "buildin",
    "debug",
    "mysql",
]


def __getattr__(name: str):
    if name == "get_common_kb_tools":
        return import_module("yuxi.agents.toolkits.kbs").get_common_kb_tools
    if name in {"buildin", "debug", "mysql"}:
        return import_module(f"yuxi.agents.toolkits.{name}")
    raise AttributeError(f"module 'yuxi.agents.toolkits' has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | set(__all__))
