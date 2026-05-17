"""
扩展组件管理器

集中管理所有第三方组件的初始化与释放。
自动发现 extensions 下子包中的 register.py 和 clean.py。
"""

import importlib
import inspect
import logging
import pkgutil

import src.api.extensions as extensions_pkg

logger = logging.getLogger(__name__)


async def _execute_extension_hook(module_filename: str, function_name: str) -> None:
    """
    遍历 extensions 下的所有子包，寻找指定文件和函数并执行。

    Args:
        module_filename: 目标文件名（如 "register" 或 "clean"）。
        function_name: 目标函数名（如 "register" 或 "clean"）。
    """
    package_path = extensions_pkg.__path__
    package_name = extensions_pkg.__name__ + "."

    for _, name, is_pkg in pkgutil.iter_modules(package_path, package_name):
        if not is_pkg:
            continue

        try:
            target_module = f"{name}.{module_filename}"
            try:
                module = importlib.import_module(target_module)
            except ImportError as e:
                if module_filename in str(e):
                    logger.debug("Extension %s has no %s.py, skipping.", name, module_filename)
                    continue
                raise

            if hasattr(module, function_name):
                func = getattr(module, function_name)
                if callable(func):
                    logger.info("Executing %s() for extension: %s", function_name, name)
                    if inspect.iscoroutinefunction(func):
                        await func()
                    else:
                        func()
            else:
                logger.debug("Module %s has no %s() function.", target_module, function_name)

        except Exception:
            logger.exception("Error executing %s for %s", function_name, name)


async def startup() -> None:
    """应用启动时初始化所有扩展。"""
    logger.info("Initializing extensions...")
    await _execute_extension_hook("register", "register")
    logger.info("Extensions initialized successfully.")


async def shutdown() -> None:
    """应用关闭时清理所有扩展。"""
    logger.info("Shutting down extensions...")
    await _execute_extension_hook("clean", "clean")
    logger.info("Extensions shutdown complete.")
